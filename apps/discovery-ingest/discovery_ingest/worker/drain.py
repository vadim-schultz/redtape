"""Claim discovery tasks, fetch targets, and report outcomes."""

from __future__ import annotations

from discovery_ingest.browser.port import BrowserClient
from discovery_ingest.budget import BudgetGuard
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.schemas import DrainReport
from discovery_ingest.worker.batch import DrainContext, run_batch
from discovery_ingest.worker.browser_spend import BrowserSpend, open_browser_spend
from discovery_ingest.worker.drain_deps import DrainDeps
from discovery_ingest.worker.drain_loop import Finish, drain_until_stop
from discovery_ingest.worker.extract_enqueue import ExtractEnqueuer
from discovery_ingest.worker.handler_table import handler_table
from discovery_ingest.worker.llm_drain import LlmDrain, open_llm_drain
from discovery_ingest.worker.llm_enqueue import LlmEnqueuer
from discovery_ingest.worker.policy import DrainPolicy
from discovery_ingest.worker.report import build_report, remaining_of
from discovery_ingest.worker.snapshot_hooks import chain
from discovery_ingest.worker.tally import Tally


def _open_spend(policy: DrainPolicy, guard: BudgetGuard, browser: BrowserClient | None) -> BrowserSpend | None:
    if not policy.drains_browser_kinds or policy.browser_budget_seconds is None:
        return None
    if browser is None:
        raise ValueError("a browser client is required to drain a browser kind")
    return open_browser_spend(policy.browser_budget_seconds, guard)


def run_worker_drain(deps: DrainDeps, policy: DrainPolicy) -> DrainReport:
    """Claim and settle batches until ``policy`` says to stop.

    ``deps.budget`` is probed once so the report says whether the shared ledger was reachable; handlers that spend a
    free allocation reserve against the same guard. A browser kind needs ``deps.browser``; with no browser time left
    today the drain stops ``browser_budget`` before it claims anything. ``deps.extractors`` serve both ``extract_page``
    and the default after-snapshot action (queue ``extract_page``); ``deps.after_snapshot`` replaces that action.

    Draining ``llm_extract`` needs ``deps.llm`` and ``policy.neuron_budget``; with no neurons left today the drain stops
    ``llm_budget`` before it claims anything. ``deps.after_extract`` runs for each page that staged mentions (no-op by
    default). ``deps.llm_enqueue`` runs after the snapshot hook of every render and queues ``llm_extract``; its failures
    are counted in the report.
    """
    client = deps.client
    guard = deps.budget or BudgetGuard(client.budget)
    guard.snapshot()
    spend, tally = _open_spend(policy, guard, deps.browser), Tally()
    if policy.drains_browser_kinds and spend is None:
        return _report(client, policy, tally, Finish("browser_budget"))
    llm_drain = open_llm_drain(policy, guard, deps.llm, deps.after_extract)
    if policy.drains_llm_kinds and llm_drain is None:
        return _report(client, policy, tally, Finish("llm_budget"))
    hook = chain(deps.after_snapshot or ExtractEnqueuer(client, deps.extractors), deps.llm_enqueue)
    ctx = DrainContext(client, deps.fetcher, policy, handler_table(deps, (deps.browser, spend, hook), llm_drain))
    finish = drain_until_stop(lambda: run_batch(ctx, tally), policy, deps.clock)
    _close_tally(tally, guard, spend, (llm_drain, deps.llm_enqueue))
    return _report(client, policy, tally, finish)


def _close_tally(
    tally: Tally, guard: BudgetGuard, spend: BrowserSpend | None, llm: tuple[LlmDrain | None, LlmEnqueuer | None]
) -> None:
    tally.ledger_unavailable = guard.ledger_unavailable
    tally.browser_seconds_used = spend.used_seconds if spend else 0.0
    for part in llm:
        if part is not None:
            part.record(tally)


def _report(client: DiscoveryIngestClient, policy: DrainPolicy, tally: Tally, finish: Finish) -> DrainReport:
    return build_report(tally, finish, remaining_of(lambda: client.tasks.summary(kinds=policy.kinds).pending_ready))
