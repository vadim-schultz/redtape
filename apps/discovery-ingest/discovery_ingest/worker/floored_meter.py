"""A usage meter that keeps a floor of the day's neuron ledger for request-time query embedding."""

from __future__ import annotations

from discovery_ingest.budget import BudgetGuard
from discovery_ingest.extract.llm.meter import RESOURCE
from discovery_ingest.translation.meter import UsageDenied, UsageMeter, UsageReservation
from discovery_ingest.translation.units import Usage


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
        return self._recheck(answer)

    def _recheck(self, reservation: UsageReservation) -> UsageReservation | UsageDenied:
        late = self._denial(0.0)
        if late is None:
            return reservation
        self._inner.refund(reservation)
        return late

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
