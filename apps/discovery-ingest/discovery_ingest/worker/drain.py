"""Claim discovery tasks, fetch targets, and report outcomes."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Protocol

from discovery_ingest.api_client import DiscoveryMachineClient
from discovery_ingest.schemas import ClaimedTask, DrainReport, FetchLogAppendRequest
from discovery_ingest.worker.enrich_metadata import handle_enrich_metadata
from discovery_ingest.worker.fetcher import PoliteUrlFetcher
from discovery_ingest.worker.policy import DrainPolicy
from discovery_ingest.worker.settle import fail_from_outcome, fail_permanently


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


@dataclass(slots=True)
class _Tally:
    """Mutable per-outcome counters for one drain."""

    batches: int = 0
    claimed: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0

    def record(self, outcome: str) -> None:
        """Count one task outcome label."""
        if outcome == "completed":
            self.completed += 1
        elif outcome == "failed":
            self.failed += 1
        else:
            self.skipped += 1


def _run_batch(
    client: DiscoveryMachineClient,
    fetcher: PoliteUrlFetcher,
    policy: DrainPolicy,
    tally: _Tally,
) -> int:
    """Claim one batch, settle every task in it, and return the batch size."""
    items = client.claim_tasks(limit=policy.max_tasks, kinds=policy.kinds).items
    tally.batches += 1
    tally.claimed += len(items)
    for task in items:
        tally.record(_dispatch_task(task, client=client, fetcher=fetcher))
    return len(items)


def run_worker_drain(
    client: DiscoveryMachineClient,
    fetcher: PoliteUrlFetcher,
    policy: DrainPolicy,
    *,
    clock: Callable[[], float] = time.monotonic,
) -> DrainReport:
    """Claim and settle batches until ``policy`` says to stop."""
    started = clock()
    tally = _Tally()
    while True:
        last_claimed = _run_batch(client, fetcher, policy, tally)
        reason = policy.stop_reason(batches=tally.batches, last_claimed=last_claimed, elapsed=clock() - started)
        if reason is not None:
            return DrainReport(**asdict(tally), stop_reason=reason)


def _dispatch_task(
    task: ClaimedTask,
    *,
    client: DiscoveryMachineClient,
    fetcher: PoliteUrlFetcher,
) -> str:
    handler = _TASK_HANDLERS.get(task.kind)
    if handler is None:
        return fail_permanently(client, task.id, f"unsupported task kind: {task.kind}")
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
    if outcome.failed:
        return fail_from_outcome(client, task.id, outcome)
    client.complete_task(task.id)
    return "completed"


_TASK_HANDLERS: dict[str, _TaskHandler] = {
    "fetch_url": _handle_fetch_url,
    "enrich_metadata": handle_enrich_metadata,
}
