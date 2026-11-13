"""One batch of snapshot tasks: claim up to five, settle each page in claim order, and hand back what a stop leaves open."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.schemas import ClaimedSnapshotTask
from discovery_ingest.snapshot_translation import SkippedPage, SourcePage, prepare_page
from discovery_ingest.translation.engine import TranslationEngine
from discovery_ingest.translation.meter import UsageMeter
from discovery_ingest.translation.metered import MeteredTranslator
from discovery_ingest.worker.batch import BatchResult
from discovery_ingest.worker.lease_settle import refusals_as_stops, release_batch
from discovery_ingest.worker.open_tasks import OpenTasks
from discovery_ingest.worker.policy import DrainPolicy
from discovery_ingest.worker.snapshot_fetch import SnapshotGone, fetch_page, release_pruned
from discovery_ingest.worker.snapshot_settle import PageSettler
from discovery_ingest.worker.stop import StopDrain
from discovery_ingest.worker.tally import Tally

Settle = Callable[[PageSettler, ClaimedSnapshotTask, SourcePage], None]
_BY_OUTCOME: Mapping[str, Settle] = {"unchanged": PageSettler.unchanged, "translated": PageSettler.translated}
"""How a page with a source (not skipped) is settled, keyed by its outcome."""


@dataclass(frozen=True, slots=True)
class SnapshotContext:
    """What every batch of one drain shares: the client, the engine and its document meter, the bounds and the tally."""

    client: DiscoveryIngestClient
    engine: TranslationEngine
    meter: UsageMeter
    policy: DrainPolicy
    tally: Tally


def outcome_of(page: SourcePage, stored: str | None) -> str:
    """``unchanged`` when the cleaned text is the text already stored, which costs nothing; otherwise ``translated``."""
    return "unchanged" if page.source_hash == stored else "translated"


def settle_task(settler: PageSettler, task: ClaimedSnapshotTask) -> None:
    """Fetch and check one page, then settle it by its outcome; a pruned snapshot is released without an attempt."""
    try:
        html = fetch_page(settler.client.artifacts, task.artifact_id)
    except SnapshotGone:
        release_pruned(settler, task)
        return
    page = prepare_page(html, task.source_url)
    if isinstance(page, SkippedPage):
        settler.skipped(task, page)
        return
    _BY_OUTCOME[outcome_of(page, task.stored_source_hash)](settler, task, page)


def _settle(ctx: SnapshotContext, tasks: list[ClaimedSnapshotTask]) -> StopDrain | None:
    open_tasks = OpenTasks(tasks)
    translator = MeteredTranslator(ctx.engine, ctx.meter)
    settler = PageSettler(ctx.client, translator, ctx.engine.name, ctx.tally, open_tasks)
    try:
        with refusals_as_stops():
            for task in tasks:
                settle_task(settler, task)
    except StopDrain as stop:
        ctx.tally.released += release_batch(ctx.client.snapshots, open_tasks.remaining(), f"{stop.reason}: {stop}")
        return stop
    return None


def _claim(ctx: SnapshotContext) -> list[ClaimedSnapshotTask]:
    with refusals_as_stops():
        return ctx.client.snapshots.claim(limit=ctx.policy.max_tasks).items


def run_snapshot_batch(ctx: SnapshotContext) -> BatchResult:
    """Claim one batch and settle it; a stop signal releases what is still open and ends the drain."""
    ctx.tally.batches += 1
    try:
        tasks = _claim(ctx)
    except StopDrain as stop:
        return BatchResult(0, stop)
    ctx.tally.claimed += len(tasks)
    return BatchResult(len(tasks), _settle(ctx, tasks))
