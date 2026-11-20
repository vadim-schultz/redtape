"""Claim one batch and settle its tasks; a stop signal releases the rest of the batch."""

from __future__ import annotations

from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
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
    if ctx.policy.concurrency > 1:
        return _settle_in_waves(ctx, items, tally)
    return _settle_in_order(ctx, items, tally)


def _release_stopped(ctx: DrainContext, tally: Tally, tasks: list[ClaimedTask], stop: StopDrain) -> None:
    """Hand back the tasks a stop left open, counting the ones the API took."""
    tally.released += release_tasks(ctx.client, tasks, f"{stop.reason}: {stop}")


def _settle_in_order(ctx: DrainContext, items: list[ClaimedTask], tally: Tally) -> StopDrain | None:
    for index, task in enumerate(items):
        try:
            tally.record(_dispatch(ctx, task))
        except StopDrain as stop:
            _release_stopped(ctx, tally, items[index:], stop)
            return stop
    return None


def _settle_in_waves(ctx: DrainContext, items: list[ClaimedTask], tally: Tally) -> StopDrain | None:
    """Settle ``items`` in waves of ``policy.concurrency``; a stop lets the wave in flight finish and releases the rest."""
    size = ctx.policy.concurrency
    with ThreadPoolExecutor(max_workers=size) as pool:
        for start in range(0, len(items), size):
            stop, refused = _run_wave(ctx, pool, items[start : start + size], tally)
            if stop is not None:
                _release_stopped(ctx, tally, [*refused, *items[start + size :]], stop)
                return stop
    return None


def _run_wave(
    ctx: DrainContext, pool: ThreadPoolExecutor, wave: list[ClaimedTask], tally: Tally
) -> tuple[StopDrain | None, list[ClaimedTask]]:
    """Run every task of ``wave`` at once; record the outcomes here, and return the first stop with the tasks it refused."""
    futures = [(task, pool.submit(_dispatch, ctx, task)) for task in wave]
    stop: StopDrain | None = None
    refused: list[ClaimedTask] = []
    for task, future in futures:
        try:
            tally.record(future.result())
        except StopDrain as err:
            stop = stop or err
            refused.append(task)
    return stop, refused


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
