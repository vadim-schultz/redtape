"""Handle llm_extract tasks: read a stored snapshot, clean it, ask the model, ground the answer and stage what is left."""

from __future__ import annotations

from collections.abc import Callable

from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.extract.clean import CleanPage
from discovery_ingest.extract.llm.ground import ground
from discovery_ingest.extract.llm.mapping import MappingContext, to_items
from discovery_ingest.extract.llm.meter import NeuronMeter
from discovery_ingest.extract.llm.prompt import extractor_version
from discovery_ingest.schemas import ClaimedTask
from discovery_ingest.worker.browser_steps import Job, Settled, complete
from discovery_ingest.worker.fetcher import PoliteUrlFetcher
from discovery_ingest.worker.llm_call import ModelCaller
from discovery_ingest.worker.llm_post import post_staged
from discovery_ingest.worker.llm_runtime import LlmResources
from discovery_ingest.worker.llm_steps import counts_note, guarded, read_page, require_documents
from discovery_ingest.worker.tally import COMPLETED, COMPLETED_CAPTURE_ENQUEUE_FAILED

AfterExtract = Callable[[DiscoveryIngestClient, ClaimedTask], bool]
"""Runs once for a page that staged at least one mention; returns false when its follow-up could not be queued."""


def no_after_extract(client: DiscoveryIngestClient, task: ClaimedTask) -> bool:
    """Report success and queue no follow-up; the default when none is wired."""
    return True


class LlmExtractHandler:
    """Steps in order: read, decode, clean, reserve, call, settle, ground, post, complete, follow up."""

    def __init__(
        self, resources: LlmResources, meter: NeuronMeter, after_extract: AfterExtract = no_after_extract
    ) -> None:
        """Wire the model resources, the neuron meter and the follow-up that runs after mentions were staged."""
        self._resources = resources
        self._caller = ModelCaller(resources, meter)
        self._after_extract = after_extract

    @property
    def llm_calls(self) -> int:
        """How many model calls this handler has made, repair attempts included."""
        return self._caller.calls

    def __call__(self, task: ClaimedTask, *, client: DiscoveryIngestClient, fetcher: PoliteUrlFetcher) -> str:
        """Settle ``task`` as ``completed`` or ``failed``; raise :class:`StopDrain` when a limit ends the drain."""
        job = Job(task, client, fetcher)
        try:
            return self._pipeline(job)
        except Settled as settled:
            return settled.outcome

    def _pipeline(self, job: Job) -> str:
        cleaned = read_page(job, self._resources.max_chars)
        grounded = ground(self._caller.extract(job, cleaned), cleaned, self._resources.taxonomy)
        require_documents(job, grounded)
        mentions, edges = to_items(grounded, self._context(job.task, cleaned))
        unknown_codes = guarded(job, lambda: post_staged(job.client, mentions, edges))
        enqueued = self._after_extract(job.client, job.task)
        complete(job, counts_note(grounded, len(mentions), len(edges), unknown_codes))
        return COMPLETED if enqueued else COMPLETED_CAPTURE_ENQUEUE_FAILED

    def _context(self, task: ClaimedTask, cleaned: CleanPage) -> MappingContext:
        version = extractor_version(cleaned, self._resources.taxonomy)
        return MappingContext(task.catalogue_service_id, task.artifact_id, cleaned.language, version)
