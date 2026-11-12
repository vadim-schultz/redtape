"""Meter a translate drain: the neuron ledger with a floor kept for query embedding, or the engine's own meter."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from discovery_ingest.budget import BudgetGuard
from discovery_ingest.extract.llm.meter import RESOURCE
from discovery_ingest.translation.character_meter import CharacterMeter
from discovery_ingest.translation.meter import NeuronUsageMeter, NoMeterForUnitError, UsageMeter
from discovery_ingest.translation.subscription_meter import SubscriptionMeter
from discovery_ingest.translation.units import UsageUnit
from discovery_ingest.worker.floored_meter import Floor, FlooredMeter


@dataclass(frozen=True, slots=True)
class MeterPlan:
    """How one drain is metered: the guard of the shared ledger, the run budget, the floor and any meters of its own."""

    guard: BudgetGuard
    limit: float | None
    floor: float
    own: Mapping[UsageUnit, UsageMeter]


MeterFactory = Callable[[MeterPlan], UsageMeter | None]


def _floored_neuron_meter(plan: MeterPlan) -> UsageMeter | None:
    if plan.limit is None:
        raise ValueError("neuron_budget is required to drain translations billed in neurons")
    left = plan.guard.remaining(RESOURCE)
    if left.exhausted or left.remaining is None or left.remaining <= plan.floor:
        return None
    inner = NeuronUsageMeter(plan.guard, min(plan.limit, left.remaining))
    return FlooredMeter(inner, plan.guard, Floor(RESOURCE, plan.floor))


def _own(meter: UsageMeter) -> MeterFactory:
    return lambda _plan: meter


def _factories(plan: MeterPlan) -> dict[UsageUnit, MeterFactory]:
    return {"neurons": _floored_neuron_meter, **{unit: _own(meter) for unit, meter in plan.own.items()}}


def _subscription_meter(_guard: BudgetGuard) -> UsageMeter:
    return SubscriptionMeter()


_OWN_METERS: Mapping[UsageUnit, Callable[[BudgetGuard], UsageMeter]] = {
    "characters": CharacterMeter,
    "subscription": _subscription_meter,
}


def own_meters_for(unit: UsageUnit, guard: BudgetGuard) -> dict[UsageUnit, UsageMeter]:
    """Return the meter an engine billed in ``unit`` brings of its own, keyed by that unit; a unit on the neuron ledger has none."""
    factory = _OWN_METERS.get(unit)
    return {} if factory is None else {unit: factory(guard)}


def open_run_meter(unit: UsageUnit, plan: MeterPlan) -> UsageMeter | None:
    """Return the meter of a drain whose engine is billed in ``unit``; ``None`` when nothing may be spent today.

    An engine with a meter of its own (``plan.own``) is bounded by that meter and never touches the neuron ledger or
    its floor. Neurons get the floored ledger meter. Any other unit raises :class:`NoMeterForUnitError`.
    """
    factory = _factories(plan).get(unit)
    if factory is None:
        raise NoMeterForUnitError(f"no meter for unit {unit}")
    return factory(plan)
