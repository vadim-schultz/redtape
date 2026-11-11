"""Usage meters: reserve before a call, settle with the actual usage, refund when the provider refused.

``UsageMeter`` is what the drain meters through; the meter is chosen by the engine's usage unit. Only neurons have
one today (the existing :class:`NeuronMeter`); asking for characters raises until a character-billed adapter ships (O17).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Protocol

from discovery_ingest.budget import BudgetGuard
from discovery_ingest.extract.llm.meter import Denied, LedgerUnavailable, NeuronMeter, Reservation
from discovery_ingest.translation.units import Usage, UsageUnit


@dataclass(frozen=True, slots=True)
class UsageReservation:
    """A granted reservation: how much, for which model, and whether the ledger stood behind it."""

    usage: Usage
    model: str
    ledgered: bool


@dataclass(frozen=True, slots=True)
class UsageDenied:
    """The call must not go out: the run budget, the day's ledger, an unreachable ledger or the reserved floor left nothing to spend."""

    reason: Literal["run_budget", "ledger", "ledger_unavailable", "floor"]


class NoMeterForUnitError(LookupError):
    """No meter exists for the engine's usage unit."""


class UsageMeter(Protocol):
    """Reserve, settle and refund usage of one unit."""

    def reserve(self, usage: Usage, model: str) -> UsageReservation | UsageDenied:
        """Reserve ``usage`` for a call to ``model``."""
        ...

    def settle(self, reservation: UsageReservation, actual: Usage) -> None:
        """Replace the reservation by the actual usage."""
        ...

    def refund(self, reservation: UsageReservation) -> None:
        """Give back a reservation for a call the provider refused, so nothing was billed."""
        ...

    def exhaust(self) -> None:
        """Record that the provider's allowance is gone."""
        ...

    def remaining(self) -> float | None:
        """Return what the run may still spend, or ``None`` when unknown."""
        ...

    @property
    def used(self) -> float:
        """Return what this run has spent so far, in the meter's unit."""
        ...


class NeuronUsageMeter:
    """:class:`UsageMeter` over a :class:`NeuronMeter` (the run budget and the daily ledger)."""

    def __init__(self, guard: BudgetGuard, run_limit: float) -> None:
        """Open a neuron meter on ``guard`` with a run limit in neurons."""
        self._meter = NeuronMeter(guard, run_limit)

    @property
    def used(self) -> float:
        """Neurons this run has reserved, corrected by what was settled."""
        return self._meter.used_neurons

    def reserve(self, usage: Usage, model: str) -> UsageReservation | UsageDenied:
        """Reserve ``usage`` neurons; an unreachable ledger is retried once against the run budget alone."""
        answer = self._reserve_neurons(model, math.ceil(usage.amount))
        if isinstance(answer, Reservation):
            return UsageReservation(Usage("neurons", answer.neurons), answer.model, answer.ledgered)
        return UsageDenied("ledger_unavailable" if isinstance(answer, LedgerUnavailable) else answer.reason)

    def _reserve_neurons(self, model: str, neurons: int) -> Reservation | Denied | LedgerUnavailable:
        answer = self._meter.reserve_neurons(model, neurons)
        if not isinstance(answer, LedgerUnavailable):
            return answer
        self._meter.stop_using_ledger()
        return self._meter.reserve_neurons(model, neurons)

    def settle(self, reservation: UsageReservation, actual: Usage) -> None:
        """Replace the reservation by the actual neurons."""
        self._meter.settle_neurons(self._neuron_reservation(reservation), actual.amount)

    def refund(self, reservation: UsageReservation) -> None:
        """Give the reserved neurons back."""
        self._meter.refund(self._neuron_reservation(reservation))

    def exhaust(self) -> None:
        """Tell the ledger the day's neurons are gone."""
        self._meter.exhaust()

    def remaining(self) -> float | None:
        """Return the neurons the run budget still allows."""
        return self._meter.remaining_neurons

    @staticmethod
    def _neuron_reservation(reservation: UsageReservation) -> Reservation:
        return Reservation(reservation.model, reservation.usage.amount, reservation.ledgered)


def meter_for_unit(unit: UsageUnit, neurons: NeuronUsageMeter) -> UsageMeter:
    """Return the meter for ``unit``: ``neurons`` for neurons, otherwise raise :class:`NoMeterForUnitError`."""
    if unit == "neurons":
        return neurons
    raise NoMeterForUnitError(f"no meter for unit {unit}")
