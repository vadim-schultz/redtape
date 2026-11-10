"""Claim translation tasks, translate them with the selected engine and post the text, until the policy or a limit stops the drain."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from discovery_ingest.budget import BudgetGuard
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.schemas import DrainReport
from discovery_ingest.translation.engine import TranslationEngine
from discovery_ingest.translation.meter import UsageMeter
from discovery_ingest.translation.metered import MeteredTranslator
from discovery_ingest.translation.units import UsageUnit
from discovery_ingest.worker.drain_loop import Finish, drain_until_stop, monotonic
from discovery_ingest.worker.policy import DrainPolicy
from discovery_ingest.worker.report import build_report, remaining_of
from discovery_ingest.worker.tally import Tally
from discovery_ingest.worker.translate_batch import TranslateContext, run_translate_batch
from discovery_ingest.worker.translate_group import CountedTranslator
from discovery_ingest.worker.translate_meter import MeterPlan, open_run_meter


@dataclass(frozen=True, slots=True)
class TranslateDeps:
    """The machine client and the engine of one drain, the neuron floor kept for query embedding, and the test seams."""

    client: DiscoveryIngestClient
    engine: TranslationEngine
    reserve: float = 0.0
    own_meters: Mapping[UsageUnit, UsageMeter] = field(default_factory=dict)
    budget: BudgetGuard | None = None
    clock: Callable[[], float] = monotonic


def _neurons_spent(deps: TranslateDeps, meter: UsageMeter | None) -> float:
    if meter is None or deps.engine.usage_unit != "neurons":
        return 0.0
    return round(meter.used, 1)


def _close_tally(deps: TranslateDeps, tally: Tally, meter: UsageMeter | None, guard: BudgetGuard) -> None:
    tally.neurons_used = _neurons_spent(deps, meter)
    tally.ledger_unavailable = guard.ledger_unavailable


def _report(deps: TranslateDeps, tally: Tally, finish: Finish) -> DrainReport:
    return build_report(tally, finish, remaining_of(lambda: deps.client.translations.summary().pending_ready))


def run_translate_drain(deps: TranslateDeps, policy: DrainPolicy) -> DrainReport:
    """Claim, translate and complete batches until ``policy`` says to stop; return the report.

    For an engine billed in neurons ``policy.neuron_budget`` is required and the drain never takes the day's ledger
    below ``deps.reserve`` (decision D15); an engine billed in another unit is bounded by its own meter instead. A
    quota or budget stop releases the tasks nobody has settled, so no attempt is consumed.
    """
    guard, tally = deps.budget or BudgetGuard(deps.client.budget), Tally()
    plan = MeterPlan(guard, policy.neuron_budget, deps.reserve, deps.own_meters)
    meter = open_run_meter(deps.engine.usage_unit, plan)
    if meter is None:
        _close_tally(deps, tally, None, guard)
        return _report(deps, tally, Finish("llm_budget"))
    translator = CountedTranslator(MeteredTranslator(deps.engine, meter), tally)
    ctx = TranslateContext(deps.client, translator, deps.engine.name, policy)
    finish = drain_until_stop(lambda: run_translate_batch(ctx, tally), policy, deps.clock)
    _close_tally(deps, tally, meter, guard)
    return _report(deps, tally, finish)
