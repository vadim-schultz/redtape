"""Claim discovery tasks, fetch targets, and report outcomes."""

from __future__ import annotations

from typing import Protocol

from discovery_ingest.api_client import DiscoveryMachineApiError, DiscoveryMachineClient
from discovery_ingest.schemas import ClaimedTask, DrainReport, FetchLogAppendRequest
from discovery_ingest.worker.enrich_metadata import handle_enrich_metadata
from discovery_ingest.worker.fetcher import PoliteUrlFetcher


class _TaskHandler(Protocol):
    def __call__(
        self,
        task: ClaimedTask,
        *,
        client: DiscoveryMachineClient,
        fetcher: PoliteUrlFetcher,
    ) -> str:
        """Return outcome label: completed, failed, or skipped."""
        ...


def run_worker_drain(
    client: DiscoveryMachineClient,
    fetcher: PoliteUrlFetcher,
    *,
    max_tasks: int,
) -> DrainReport:
    """Claim up to ``max_tasks`` tasks and process each by kind."""
    if max_tasks < 1 or max_tasks > 50:
        raise ValueError("max_tasks must be between 1 and 50")
    try:
        claimed = client.claim_tasks(limit=max_tasks)
    except DiscoveryMachineApiError:
        raise
    completed = 0
    failed = 0
    skipped = 0
    for task in claimed.items:
        outcome = _dispatch_task(task, client=client, fetcher=fetcher)
        if outcome == "completed":
            completed += 1
        elif outcome == "failed":
            failed += 1
        else:
            skipped += 1
    return DrainReport(
        claimed=len(claimed.items),
        completed=completed,
        failed=failed,
        skipped=skipped,
    )


def _dispatch_task(
    task: ClaimedTask,
    *,
    client: DiscoveryMachineClient,
    fetcher: PoliteUrlFetcher,
) -> str:
    handler = _TASK_HANDLERS.get(task.kind)
    if handler is None:
        client.fail_task(task.id, error=f"unsupported task kind: {task.kind}")
        return "failed"
    return handler(task, client=client, fetcher=fetcher)


def _handle_fetch_url(
    task: ClaimedTask,
    *,
    client: DiscoveryMachineClient,
    fetcher: PoliteUrlFetcher,
) -> str:
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
    if outcome.error_message is not None or outcome.http_status is None or outcome.http_status >= 400:
        error = outcome.error_message or f"HTTP {outcome.http_status}"
        client.fail_task(task.id, error=error)
        return "failed"
    client.complete_task(task.id)
    return "completed"


_TASK_HANDLERS: dict[str, _TaskHandler] = {
    "fetch_url": _handle_fetch_url,
    "enrich_metadata": handle_enrich_metadata,
}
