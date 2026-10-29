"""Claim discovery tasks, fetch targets, and report outcomes."""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import asdict

import httpx
from pydantic import ValidationError

from discovery_ingest.api_client import DiscoveryMachineApiError, DiscoveryMachineClient
from discovery_ingest.browser.port import BrowserClient
from discovery_ingest.budget import BudgetGuard
from discovery_ingest.extract.base import Extractor
from discovery_ingest.extract.registry import EXTRACTORS
from discovery_ingest.schemas import DrainReport, StopReason
from discovery_ingest.worker.batch import BatchResult, DrainContext, run_batch
from discovery_ingest.worker.browser_spend import BrowserSpend, open_browser_spend
from discovery_ingest.worker.extract_enqueue import ExtractEnqueuer
from discovery_ingest.worker.fetcher import PoliteUrlFetcher
from discovery_ingest.worker.handler_table import handler_table
from discovery_ingest.worker.llm_drain import LlmDrain, open_llm_drain
from discovery_ingest.worker.llm_enqueue import LlmEnqueuer
from discovery_ingest.worker.llm_extract import AfterExtract, no_after_extract
from discovery_ingest.worker.llm_runtime import LlmResources
from discovery_ingest.worker.policy import DrainPolicy
from discovery_ingest.worker.render import AfterSnapshot
from discovery_ingest.worker.snapshot_hooks import chain
from discovery_ingest.worker.tally import Tally


def _open_spend(policy: DrainPolicy, guard: BudgetGuard, browser: BrowserClient | None) -> BrowserSpend | None:
    if not policy.drains_browser_kinds or policy.browser_budget_seconds is None:
        return None
    if browser is None:
        raise ValueError("a browser client is required to drain a browser kind")
    return open_browser_spend(policy.browser_budget_seconds, guard)


def _stop(batch: BatchResult, policy: DrainPolicy, tally: Tally, elapsed: float) -> StopReason | None:
    if batch.stop is not None:
        return batch.stop.reason
    return policy.stop_reason(batches=tally.batches, last_claimed=batch.size, elapsed=elapsed)


def _drain_batches(ctx: DrainContext, tally: Tally, clock: Callable[[], float]) -> tuple[StopReason, str | None]:
    """Run batches until a stop reason appears; return it with the error detail of an ``error`` stop."""
    started = clock()
    while True:
        batch = run_batch(ctx, tally)
        reason = _stop(batch, ctx.policy, tally, clock() - started)
        if reason is not None:
            return reason, str(batch.stop) if reason == "error" and batch.stop is not None else None


def run_worker_drain(
    client: DiscoveryMachineClient,
    fetcher: PoliteUrlFetcher,
    policy: DrainPolicy,
    *,
    clock: Callable[[], float] = time.monotonic,
    budget: BudgetGuard | None = None,
    browser: BrowserClient | None = None,
    after_snapshot: AfterSnapshot | None = None,
    extractors: Sequence[Extractor] = EXTRACTORS,
    llm: LlmResources | None = None,
    after_extract: AfterExtract = no_after_extract,
    llm_enqueue: LlmEnqueuer | None = None,
) -> DrainReport:
    """Claim and settle batches until ``policy`` says to stop.

    ``budget`` is probed once so the report says whether the shared ledger was reachable; handlers that spend a free
    allocation reserve against the same guard. A browser kind needs ``browser``; with no browser time left today the
    drain stops ``browser_budget`` before it claims anything. ``extractors`` serve both ``extract_page`` and the default
    after-snapshot action (queue ``extract_page``); passing ``after_snapshot`` replaces that action.

    Draining ``llm_extract`` needs ``llm`` and ``policy.neuron_budget``; with no neurons left today the drain stops
    ``llm_budget`` before it claims anything. ``after_extract`` runs for each page that staged mentions (no-op by default). ``llm_enqueue`` runs after the
    snapshot hook of every render and queues ``llm_extract``; its failures are counted in the report.
    """
    guard = budget or BudgetGuard(client)
    guard.snapshot()
    spend, tally = _open_spend(policy, guard, browser), Tally()
    if policy.drains_browser_kinds and spend is None:
        return _report(client, policy, tally, "browser_budget")
    llm_drain = open_llm_drain(policy, guard, llm, after_extract)
    if policy.drains_llm_kinds and llm_drain is None:
        return _report(client, policy, tally, "llm_budget")
    hook = chain(after_snapshot or ExtractEnqueuer(client, extractors), llm_enqueue)
    ctx = DrainContext(client, fetcher, policy, handler_table(extractors, (browser, spend, hook), llm_drain))
    reason, error = _drain_batches(ctx, tally, clock)
    _close_tally(tally, guard, spend, (llm_drain, llm_enqueue))
    return _report(client, policy, tally, reason, error=error)


def _close_tally(
    tally: Tally, guard: BudgetGuard, spend: BrowserSpend | None, llm: tuple[LlmDrain | None, LlmEnqueuer | None]
) -> None:
    tally.ledger_unavailable = guard.ledger_unavailable
    tally.browser_seconds_used = spend.used_seconds if spend else 0.0
    for part in llm:
        if part is not None:
            part.record(tally)


def _remaining(client: DiscoveryMachineClient, policy: DrainPolicy) -> int | None:
    """Return the ready backlog for the drained kinds, or ``None`` when the summary is unavailable."""
    try:
        return client.get_task_summary(kinds=policy.kinds).pending_ready
    except (DiscoveryMachineApiError, httpx.HTTPError, ValidationError):
        return None


def _report(
    client: DiscoveryMachineClient, policy: DrainPolicy, tally: Tally, reason: StopReason, *, error: str | None = None
) -> DrainReport:
    remaining = _remaining(client, policy)
    return DrainReport(
        **asdict(tally),
        remaining=remaining,
        remaining_unknown=remaining is None,
        stop_reason=reason,
        succeeded=reason != "error",
        error=error,
    )
