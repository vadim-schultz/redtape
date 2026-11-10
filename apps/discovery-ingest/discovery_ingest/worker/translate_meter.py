"""Meter a translate drain: the neuron ledger with a floor kept for query embedding, or the engine's own meter."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from discovery_ingest.budget import BudgetGuard
from discovery_ingest.extract.llm.meter import RESOURCE
from discovery_ingest.translation.meter import (
    NeuronUsageMeter,
    NoMeterForUnitError,
    UsageDenied,
    UsageMeter,
    UsageReservation,
)
from discovery_ingest.translation.units import Usage, UsageUnit


@dataclass(frozen=True, slots=True)
class MeterPlan:
    """How one drain is metered: the guard of the shared ledger, the run budget, the floor and any meters of its own."""

    guard: BudgetGuard
    limit: float | None
    floor: float
    own: Mapping[UsageUnit, UsageMeter]


class FlooredMeter:
    """A :class:`UsageMeter` that denies a reservation which would leave the day's ledger below ``floor`` neurons.

    The floor is what request-time query embedding (decision D1) lives on. The ledger is read before every
    reservation; one that cannot be read is a denial, because the floor could not be proved.
    """

    def __init__(self, inner: UsageMeter, guard: BudgetGuard, floor: float) -> None:
        """Wrap ``inner`` so that ``floor`` neurons of the day's ledger stay untouched."""
        self._inner = inner
        self._guard = guard
        self._floor = floor

    @property
    def used(self) -> float:
        """Return the neurons this run has spent."""
        return self._inner.used

    def reserve(self, usage: Usage, model: str) -> UsageReservation | UsageDenied:
        """Reserve ``usage`` unless the ledger would end below the floor or cannot be read.

        The floor is checked before the reserve and again after it: a spender that raced the first check is caught by
        the second, and the reservation is given back.
        """
        denial = self._denial(usage.amount)
        if denial is not None:
            return denial
        answer = self._inner.reserve(usage, model)
        if isinstance(answer, UsageDenied):
            return answer
        late = self._denial(0.0)
        if late is not None:
            self._inner.refund(answer)
        return late or answer

    def _denial(self, spending: float) -> UsageDenied | None:
        left = self._guard.remaining(RESOURCE).remaining
        if left is None:
            return UsageDenied("ledger_unavailable")
        return UsageDenied("floor") if left - spending < self._floor else None

    def settle(self, reservation: UsageReservation, actual: Usage) -> None:
        """Replace the reservation by the actual neurons."""
        self._inner.settle(reservation, actual)

    def refund(self, reservation: UsageReservation) -> None:
        """Give the reserved neurons back."""
        self._inner.refund(reservation)

    def exhaust(self) -> None:
        """Tell the ledger the day's neurons are gone."""
        self._inner.exhaust()

    def remaining(self) -> float | None:
        """Return the neurons the run budget still allows."""
        return self._inner.remaining()


MeterFactory = Callable[[MeterPlan], UsageMeter | None]


def _floored_neuron_meter(plan: MeterPlan) -> UsageMeter | None:
    if plan.limit is None:
        raise ValueError("neuron_budget is required to drain translations billed in neurons")
    left = plan.guard.remaining(RESOURCE)
    if left.exhausted or left.remaining is None or left.remaining <= plan.floor:
        return None
    inner = NeuronUsageMeter(plan.guard, min(plan.limit, left.remaining))
    return FlooredMeter(inner, plan.guard, plan.floor)


def _own(meter: UsageMeter) -> MeterFactory:
    return lambda _plan: meter


def _factories(plan: MeterPlan) -> dict[UsageUnit, MeterFactory]:
    return {"neurons": _floored_neuron_meter, **{unit: _own(meter) for unit, meter in plan.own.items()}}


def open_run_meter(unit: UsageUnit, plan: MeterPlan) -> UsageMeter | None:
    """Return the meter of a drain whose engine is billed in ``unit``; ``None`` when nothing may be spent today.

    An engine with a meter of its own (``plan.own``) is bounded by that meter and never touches the neuron ledger or
    its floor. Neurons get the floored ledger meter. Any other unit raises :class:`NoMeterForUnitError`.
    """
    factory = _factories(plan).get(unit)
    if factory is None:
        raise NoMeterForUnitError(f"no meter for unit {unit}")
    return factory(plan)
