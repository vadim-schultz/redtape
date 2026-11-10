"""The neuron meter: reserve before a model call, settle with the real usage after, under the run budget."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from discovery_ingest.budget import BudgetGuard
from discovery_ingest.budget_models import BudgetResource
from discovery_ingest.extract.llm.client import LlmResult
from discovery_ingest.extract.llm.ledger_reserve import reserve_up_to
from discovery_ingest.extract.llm.prices import actual_neurons, estimate

RESOURCE: BudgetResource = "neurons"


@dataclass(frozen=True, slots=True)
class Reservation:
    """A granted reservation; ``ledgered`` is false when only the run budget stood behind it."""

    model: str
    neurons: float
    ledgered: bool


@dataclass(frozen=True, slots=True)
class Denied:
    """The call must not go out: the run budget or the day's ledger has too few neurons left."""

    reason: Literal["run_budget", "ledger"]


@dataclass(frozen=True, slots=True)
class LedgerUnavailable:
    """The ledger did not answer after the run started; the caller releases its tasks."""


class NeuronMeter:
    """Reserve and settle neurons against the run budget and, when it was reachable at the start, the ledger."""

    def __init__(self, guard: BudgetGuard, run_limit: float, *, use_ledger: bool = True) -> None:
        """Set the run budget in neurons; ``use_ledger`` is false when the ledger was unreachable at the start."""
        self._guard = guard
        self._limit = run_limit
        self._use_ledger = use_ledger
        self._used = 0.0

    @property
    def used_neurons(self) -> float:
        """Neurons this run has reserved, corrected by the usage the provider reported."""
        return self._used

    @property
    def remaining_neurons(self) -> float:
        """Neurons the run budget still allows, never below zero."""
        return max(self._limit - self._used, 0.0)

    @property
    def ledger_unavailable(self) -> bool:
        """Whether the ledger has failed to answer at any point of this run."""
        return self._guard.ledger_unavailable

    def reserve(self, model: str, input_chars: int, max_tokens: int) -> Reservation | Denied | LedgerUnavailable:
        """Reserve the estimate for one call; raises :class:`UnknownModelError` for a model without a price."""
        return self.reserve_neurons(model, estimate(model, input_chars, max_tokens))

    def reserve_neurons(self, model: str, neurons: int) -> Reservation | Denied | LedgerUnavailable:
        """Reserve ``neurons`` for a call to ``model`` whose cost the caller has already estimated."""
        if self._run_budget_reached():
            return Denied("run_budget")
        granted = self._ledger_grant(neurons)
        return granted if isinstance(granted, Denied | LedgerUnavailable) else self._grant(model, granted)

    def settle(self, reservation: Reservation, result: LlmResult) -> None:
        """Replace the reservation by the real cost (reported neurons, else priced tokens); keep it when neither exists."""
        actual = actual_neurons(result)
        if actual is not None:
            self.settle_neurons(reservation, actual)

    def settle_neurons(self, reservation: Reservation, actual: float) -> None:
        """Replace the reservation by ``actual`` neurons, the cost the caller measured itself."""
        self._correct(reservation, actual - reservation.neurons)

    def refund(self, reservation: Reservation) -> None:
        """Give back a reservation for a call the provider provably refused (quota or token), so nothing was billed."""
        self._correct(reservation, -reservation.neurons)

    def stop_using_ledger(self) -> None:
        """Rely on the run budget alone from now on; call it after :class:`LedgerUnavailable` (the outage stays reported)."""
        self._use_ledger = False

    def exhaust(self) -> None:
        """Tell the ledger the day's neurons are gone (a provider quota error)."""
        if self._use_ledger:
            self._guard.exhaust(RESOURCE)

    def _run_budget_reached(self) -> bool:
        """Whether the run has used its budget; below it a call may still go out and pass it by its own cost."""
        return self._used >= self._limit

    def _correct(self, reservation: Reservation, delta: float) -> None:
        self._used += delta
        if reservation.ledgered:
            self._guard.adjust(RESOURCE, delta)

    def _ledger_grant(self, neurons: int) -> float | Denied | LedgerUnavailable:
        """Return the neurons the ledger grants (the estimate, or what is left of the day), or why it did not."""
        if not self._use_ledger:
            return neurons
        grant = reserve_up_to(self._guard, RESOURCE, neurons)
        if grant.ledger_unavailable:
            return LedgerUnavailable()
        return grant.amount if grant.amount > 0 else Denied("ledger")

    def _grant(self, model: str, neurons: float) -> Reservation:
        self._used += neurons
        return Reservation(model, neurons, ledgered=self._use_ledger)


def open_neuron_meter(limit: float, guard: BudgetGuard) -> NeuronMeter | None:
    """Return the meter for a run, capped by what the ledger has left today; ``None`` when nothing can be spent."""
    left = guard.remaining(RESOURCE)
    if left.exhausted or (left.remaining is not None and left.remaining <= 0):
        return None
    if left.remaining is None:
        return NeuronMeter(guard, limit, use_ledger=False)
    return NeuronMeter(guard, min(limit, left.remaining))
