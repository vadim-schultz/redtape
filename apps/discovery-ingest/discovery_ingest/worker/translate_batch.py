"""Claim one batch, translate its calls within the concurrency bound, settle them, and hand back what a stop leaves open."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.translation.glossary import GlossaryMode
from discovery_ingest.translation.repair import Translator
from discovery_ingest.translation.units import CallLimits
from discovery_ingest.translation_models import PriorityBand
from discovery_ingest.worker.batch import BatchResult
from discovery_ingest.worker.lease_settle import refusals_as_stops, release_batch
from discovery_ingest.worker.open_tasks import OpenTasks
from discovery_ingest.worker.policy import DrainPolicy
from discovery_ingest.worker.stop import StopDrain
from discovery_ingest.worker.tally import Tally
from discovery_ingest.worker.translate_group import Tasks, by_call
from discovery_ingest.worker.translate_settle import BatchState
from discovery_ingest.worker.translate_window import Window, settle_window


@dataclass(frozen=True, slots=True)
class TranslateContext:
    """Everything one translate drain shares across batches: the client, the translator, the bounds, the engine's limits, the glossary mode and the priority band its claims take."""

    client: DiscoveryIngestClient
    translator: Translator
    engine: str
    policy: DrainPolicy
    limits: CallLimits
    glossary: GlossaryMode
    band: PriorityBand


def _settle_groups(ctx: TranslateContext, tasks: Tasks, state: BatchState) -> None:
    calls = by_call(tasks, ctx.limits.units_per_call)
    size = min(ctx.policy.concurrency, ctx.limits.concurrency)
    with ThreadPoolExecutor(max_workers=size) as pool, refusals_as_stops():
        window = Window(ctx.translator, pool, size, ctx.glossary)
        try:
            settle_window(window, calls, state)
        finally:
            window.halt.set()


def _settle(ctx: TranslateContext, tasks: Tasks, tally: Tally) -> StopDrain | None:
    if not tasks:
        return None
    state = BatchState(ctx.client, ctx.engine, OpenTasks(tasks), tally)
    try:
        _settle_groups(ctx, tasks, state)
    except StopDrain as stop:
        tally.released += release_batch(ctx.client.translations, state.open_tasks.remaining(), f"{stop.reason}: {stop}")
        return stop
    return None


def _claim(ctx: TranslateContext) -> Tasks:
    with refusals_as_stops():
        claim = ctx.client.translations.claim(limit=ctx.policy.max_tasks, engine=ctx.engine, band=ctx.band)
        return claim.items


def run_translate_batch(ctx: TranslateContext, tally: Tally) -> BatchResult:
    """Claim one batch and settle it; a stop signal releases what is still open and ends the drain."""
    tally.batches += 1
    try:
        tasks = _claim(ctx)
    except StopDrain as stop:
        return BatchResult(0, stop)
    tally.claimed += len(tasks)
    return BatchResult(len(tasks), _settle(ctx, tasks, tally))
