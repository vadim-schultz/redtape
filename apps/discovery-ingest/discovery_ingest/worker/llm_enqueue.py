"""The after_snapshot action that queues llm_extract for a stored snapshot, behind the ``LLM_ENQUEUE`` switch."""

from __future__ import annotations

import hashlib
import sys

import httpx
from pydantic import ValidationError

from discovery_ingest.api_client import DiscoveryMachineApiError, DiscoveryMachineClient
from discovery_ingest.artifacts import ArtifactRead
from discovery_ingest.extract.clean import CLEAN_VERSION
from discovery_ingest.extract.llm.prompt import PROMPT_VERSION
from discovery_ingest.schemas import ClaimedTask, TaskEnqueueRequest
from discovery_ingest.worker.tally import Tally

LLM_PRIORITY = 200
"""After renders (100) and before screenshots (300), because the queue takes lower numbers first."""


def llm_input_key(model: str) -> str:
    """Return ``llm:`` and eight hex digits of ``model | prompt version | clean version``.

    A different model, prompt or cleaner is a different key, so ``llm requeue`` can run a page again; the same
    versions give the same key, and the queue's identity then refuses a second task for the page.
    """
    digest = hashlib.sha256(f"{model}|{PROMPT_VERSION}|{CLEAN_VERSION}".encode()).hexdigest()
    return f"llm:{digest[:8]}"


def llm_extract_request(artifact: ArtifactRead, model: str) -> TaskEnqueueRequest:
    """Return the ``llm_extract`` enqueue request for ``artifact`` under the current versions of ``model``."""
    return TaskEnqueueRequest(
        catalogue_service_id=artifact.catalogue_service_id,
        kind="llm_extract",
        target_url=artifact.source_url,
        priority=LLM_PRIORITY,
        input_key=llm_input_key(model),
        artifact_id=artifact.id,
    )


class LlmEnqueuer:
    """An :data:`~discovery_ingest.worker.render.AfterSnapshot` hook: one ``llm_extract`` per snapshot and version."""

    def __init__(self, client: DiscoveryMachineClient, model: str) -> None:
        """Enqueue through ``client`` for extraction by ``model``."""
        self._client = client
        self._model = model
        self.failed = 0

    def __call__(self, task: ClaimedTask, artifact: ArtifactRead) -> None:
        """Enqueue ``llm_extract`` for ``artifact``; an error is logged and counted in :attr:`failed`, never raised."""
        try:
            self._client.enqueue_task(llm_extract_request(artifact, self._model))
        except (DiscoveryMachineApiError, httpx.HTTPError, ValidationError) as err:
            self.failed += 1
            print(f"llm enqueue failed for {artifact.source_url}: {err}", file=sys.stderr)

    def record(self, tally: Tally) -> None:
        """Copy the number of failed enqueues into ``tally``."""
        tally.llm_enqueue_failed = self.failed
