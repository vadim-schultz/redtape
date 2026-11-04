"""Claim one batch and settle its tasks; a stop signal releases the rest of the batch."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from discovery_ingest.client import DiscoveryIngestClient, DiscoveryMachineApiError
from discovery_ingest.schemas import ClaimedTask, DiscoveryTaskKind
from discovery_ingest.worker.fetcher import PoliteUrlFetcher
from discovery_ingest.worker.policy import DrainPolicy
from discovery_ingest.worker.release import release_tasks
from discovery_ingest.worker.settle import fail_permanently
from discovery_ingest.worker.stop import StopDrain
from discovery_ingest.worker.tally import Tally


class TaskHandler(Protocol):
    """Settle one claimed task and return its outcome label (``completed``, ``failed`` or ``skipped``)."""

    def __call__(self, task: ClaimedTask, *, client: DiscoveryIngestClient, fetcher: PoliteUrlFetcher) -> str:
        """Settle ``task``; raise :class:`StopDrain` when a limit ends the drain."""
        ...


@dataclass(frozen=True, slots=True)
class DrainContext:
    """Everything one drain shares across batches."""

    client: DiscoveryIngestClient
    fetcher: PoliteUrlFetcher
    policy: DrainPolicy
    handlers: Mapping[DiscoveryTaskKind, TaskHandler]


@dataclass(frozen=True, slots=True)
class BatchResult:
    """The size of the batch and the stop signal that cut it short, if any."""

    size: int
    stop: StopDrain | None = None


def run_batch(ctx: DrainContext, tally: Tally) -> BatchResult:
    """Claim one batch, settle every task in it, and return its size and any stop signal."""
    items = ctx.client.tasks.claim(limit=ctx.policy.max_tasks, kinds=ctx.policy.kinds).items
    tally.batches += 1
    tally.claimed += len(items)
    return BatchResult(len(items), _settle(ctx, items, tally))


def _settle(ctx: DrainContext, items: list[ClaimedTask], tally: Tally) -> StopDrain | None:
    for index, task in enumerate(items):
        try:
            tally.record(_dispatch(ctx, task))
        except StopDrain as stop:
            tally.released += release_tasks(ctx.client, items[index:], f"{stop.reason}: {stop}")
            return stop
    return None


def _dispatch(ctx: DrainContext, task: ClaimedTask) -> str:
    handler = ctx.handlers.get(task.kind)
    if handler is None:
        return fail_permanently(ctx.client, task.id, f"unsupported task kind: {task.kind}")
    try:
        return handler(task, client=ctx.client, fetcher=ctx.fetcher)
    except DiscoveryMachineApiError as err:
        if err.is_database_limit:
            raise StopDrain("db_limit", err.detail) from err
        raise
