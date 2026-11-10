"""Claim one batch of translation tasks, settle it locale by locale and hand back what a stop leaves open."""

from __future__ import annotations

from dataclasses import dataclass

from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.translation.repair import Translator
from discovery_ingest.worker.batch import BatchResult
from discovery_ingest.worker.lease_settle import refusals_as_stops, release_batch
from discovery_ingest.worker.open_tasks import OpenTasks
from discovery_ingest.worker.policy import DrainPolicy
from discovery_ingest.worker.stop import StopDrain
from discovery_ingest.worker.tally import Tally
from discovery_ingest.worker.translate_group import Tasks, by_locale, settle_group
from discovery_ingest.worker.translate_settle import BatchState


@dataclass(frozen=True, slots=True)
class TranslateContext:
    """Everything one translate drain shares across batches: the client, the metered translator and the bounds."""

    client: DiscoveryIngestClient
    translator: Translator
    engine: str
    policy: DrainPolicy


def _settle_groups(ctx: TranslateContext, tasks: Tasks, state: BatchState) -> None:
    with refusals_as_stops():
        for group in by_locale(tasks):
            settle_group(ctx.translator, state, group)


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
        return ctx.client.translations.claim(limit=ctx.policy.max_tasks).items


def run_translate_batch(ctx: TranslateContext, tally: Tally) -> BatchResult:
    """Claim one batch and settle it; a stop signal releases what is still open and ends the drain."""
    tally.batches += 1
    try:
        tasks = _claim(ctx)
    except StopDrain as stop:
        return BatchResult(0, stop)
    tally.claimed += len(tasks)
    return BatchResult(len(tasks), _settle(ctx, tasks, tally))
