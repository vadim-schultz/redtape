"""Handle fetch_url tasks: polite GET, log the attempt with its body hash, enqueue the render the API asks for, then settle."""

from __future__ import annotations

import hashlib

from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.schemas import ClaimedTask, FetchLogAppendRequest
from discovery_ingest.worker.fetcher import PoliteUrlFetcher
from discovery_ingest.worker.outcome import FetchOutcome
from discovery_ingest.worker.render_enqueue import enqueue_render, render_order
from discovery_ingest.worker.settle import fail_from_outcome
from discovery_ingest.worker.tally import COMPLETED, COMPLETED_RENDER_ENQUEUE_FAILED

FINAL_URL_LIMIT = 2048
"""The longest final url the API accepts on a fetch log; a longer one is logged without a verdict."""


def handle_fetch_url(task: ClaimedTask, *, client: DiscoveryIngestClient, fetcher: PoliteUrlFetcher) -> str:
    """Fetch the target, log it, enqueue the render that the API's verdict asks for, then complete or fail the task."""
    outcome = fetcher.get(task.target_url)
    verdict = client.tasks.append_fetch(task.id, _fetch_log_entry(outcome))
    if outcome.failed:
        return fail_from_outcome(client, task.id, outcome)
    order = render_order(task, outcome, verdict)
    enqueued = order is None or enqueue_render(client, order)
    client.tasks.complete(task.id)
    return COMPLETED if enqueued else COMPLETED_RENDER_ENQUEUE_FAILED


def _fetch_log_entry(outcome: FetchOutcome) -> FetchLogAppendRequest:
    """Build the fetch-log row for ``outcome``: its status and size, the sha256 of the body read, and the final url."""
    return FetchLogAppendRequest(
        http_status=outcome.http_status,
        content_type=outcome.content_type,
        byte_length=outcome.byte_length,
        error_message=outcome.error_message,
        body_sha256=_sha256(outcome.body),
        final_url=_final_url(outcome),
    )


def _sha256(body: bytes | None) -> str | None:
    """Return the hex sha256 of ``body``, or ``None`` when the fetch read no body."""
    return None if body is None else hashlib.sha256(body).hexdigest()


def _final_url(outcome: FetchOutcome) -> str | None:
    """Return the url the fetch landed on, or ``None`` when there is none or the API would refuse it."""
    final = outcome.final_url
    if final is None or len(final) > FINAL_URL_LIMIT:
        return None
    return final
