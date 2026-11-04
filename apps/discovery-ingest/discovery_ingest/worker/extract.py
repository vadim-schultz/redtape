"""Handle extract_page tasks: read a stored snapshot, run its extractor and record the mentions it finds."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID

from pydantic import ValidationError

from discovery_ingest.artifacts import ArtifactContent
from discovery_ingest.client import DiscoveryIngestClient, DiscoveryMachineApiError
from discovery_ingest.extract.base import Extractor, PageContext
from discovery_ingest.extract.decode import decode_html
from discovery_ingest.extract.registry import EXTRACTORS, find_extractor
from discovery_ingest.mentions import MentionItem
from discovery_ingest.schemas import ClaimedTask
from discovery_ingest.worker.capture_enqueue import enqueue_screenshot_for_mentions
from discovery_ingest.worker.fetcher import PoliteUrlFetcher
from discovery_ingest.worker.mention_post import post_mention_chunks
from discovery_ingest.worker.settle import fail_from_api_error, fail_permanently
from discovery_ingest.worker.tally import COMPLETED, COMPLETED_CAPTURE_ENQUEUE_FAILED


class _ExtractorFailed(Exception):
    """An extractor raised; the message names it and its version."""


class ExtractPageHandler:
    """Steps in order: fetch the snapshot, resolve the extractor, decode and extract, post, complete."""

    def __init__(self, extractors: Sequence[Extractor] = EXTRACTORS) -> None:
        """Dispatch through ``extractors``; production passes the registry, tests pass fakes."""
        self._extractors = extractors

    def __call__(self, task: ClaimedTask, *, client: DiscoveryIngestClient, fetcher: PoliteUrlFetcher) -> str:
        """Settle ``task`` as ``completed`` or ``failed``; the page itself is never fetched (``fetcher`` is unused)."""
        try:
            return self._run(task, client)
        except _ExtractorFailed as err:
            return fail_permanently(client, task.id, str(err))
        except DiscoveryMachineApiError as err:
            return _api_refused(client, task, err)

    def _run(self, task: ClaimedTask, client: DiscoveryIngestClient) -> str:
        if task.artifact_id is None:
            return fail_permanently(client, task.id, "extract_page task has no artifact_id")
        content = client.artifacts.content(task.artifact_id)
        extractor = find_extractor(task.target_url, content.content_type, self._extractors)
        if extractor is None:
            return _complete(client, task, "no_extractor")
        items = _valid_items(task, task.artifact_id, _extract(extractor, task, task.artifact_id, content))
        if not items:
            return _complete(client, task, "no_mentions")
        post_mention_chunks(client, items)
        return _complete_after_capture_enqueue(client, task)


def _api_refused(client: DiscoveryIngestClient, task: ClaimedTask, err: DiscoveryMachineApiError) -> str:
    """Fail the task on an API refusal (5xx retryable); the database limit propagates so the drain stops."""
    if err.is_database_limit:
        raise err
    return fail_from_api_error(client, task.id, err)


def _complete(client: DiscoveryIngestClient, task: ClaimedTask, note: str | None) -> str:
    client.tasks.complete(task.id, note=note)
    return "completed"


def _complete_after_capture_enqueue(client: DiscoveryIngestClient, task: ClaimedTask) -> str:
    """Queue the page's screenshot (D13), then complete; a failed enqueue is counted and never fails the task."""
    enqueued = enqueue_screenshot_for_mentions(client, task)
    _complete(client, task, None)
    return COMPLETED if enqueued else COMPLETED_CAPTURE_ENQUEUE_FAILED


def _extract(extractor: Extractor, task: ClaimedTask, artifact_id: UUID, content: ArtifactContent) -> list[MentionItem]:
    ctx = PageContext(task.catalogue_service_id, task.target_url, None, artifact_id)
    try:
        return extractor.extract(decode_html(content.data, content.content_type), ctx)
    except Exception as err:  # an extractor is hand-written per host; its failure must settle the task, not the drain
        raise _ExtractorFailed(f"extractor {extractor.id}@{extractor.version} failed: {err!r}") from err


def _valid_items(task: ClaimedTask, artifact_id: UUID, items: Sequence[MentionItem]) -> list[MentionItem]:
    """Tie every mention to the task's catalogue row and snapshot; drop the ones that fail validation."""
    tie = {"catalogue_service_id": task.catalogue_service_id, "artifact_id": artifact_id}
    checked = (_validated(item, tie) for item in items)
    return [item for item in checked if item is not None]


def _validated(item: MentionItem, tie: Mapping[str, UUID]) -> MentionItem | None:
    try:
        return MentionItem.model_validate({**item.model_dump(), **tie})
    except ValidationError:
        return None
