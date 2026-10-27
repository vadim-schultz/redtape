"""Handle fetch_url tasks: polite GET, log the attempt, complete or fail."""

from __future__ import annotations

from discovery_ingest.api_client import DiscoveryMachineClient
from discovery_ingest.schemas import ClaimedTask, FetchLogAppendRequest
from discovery_ingest.worker.fetcher import PoliteUrlFetcher
from discovery_ingest.worker.render_enqueue import enqueue_render
from discovery_ingest.worker.settle import fail_from_outcome
from discovery_ingest.worker.tally import COMPLETED, COMPLETED_RENDER_ENQUEUE_FAILED


def handle_fetch_url(task: ClaimedTask, *, client: DiscoveryMachineClient, fetcher: PoliteUrlFetcher) -> str:
    """Fetch the target, log it, enqueue the follow-up render for a real HTML page, then complete or fail the task."""
    outcome = fetcher.get(task.target_url)
    client.append_fetch(
        task.id,
        FetchLogAppendRequest(
            http_status=outcome.http_status,
            content_type=outcome.content_type,
            byte_length=outcome.byte_length,
            error_message=outcome.error_message,
        ),
    )
    if outcome.failed:
        return fail_from_outcome(client, task.id, outcome)
    enqueued = enqueue_render(client, task, outcome)
    client.complete_task(task.id)
    return COMPLETED if enqueued else COMPLETED_RENDER_ENQUEUE_FAILED
