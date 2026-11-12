"""The character meter: reserve a call's exact characters on the monthly ledger, then settle to what Azure bills.

A reservation is all or nothing. A partial grant would still bill the call in full, so a refused reserve is a denial.
The drain may run calls from several threads, so the reserve and the correction of the in-process count are locked.
"""

from __future__ import annotations

import threading

from discovery_ingest.budget import BudgetGuard, Reserved
from discovery_ingest.translation.meter import CHARACTER_RESOURCE, UsageDenied, UsageReservation
from discovery_ingest.translation.units import Usage


class CharacterMeter:
    """A :class:`~discovery_ingest.translation.meter.UsageMeter` over ``azure_translator_chars``, safe to share between calls."""

    def __init__(self, guard: BudgetGuard) -> None:
        """Meter through ``guard``; nothing is reserved until the first call."""
        self._guard = guard
        self._lock = threading.Lock()
        self._used = 0.0

    @property
    def used(self) -> float:
        """The characters this run has reserved, corrected by what was settled."""
        with self._lock:
            return self._used

    def reserve(self, usage: Usage, model: str) -> UsageReservation | UsageDenied:
        """Reserve all of ``usage`` or nothing: a refusal is ``ledger``, an unreadable ledger ``ledger_unavailable``."""
        with self._lock:
            answer = self._guard.reserve(CHARACTER_RESOURCE, usage.amount)
            return self._granted(usage, model, answer)

    def settle(self, reservation: UsageReservation, actual: Usage) -> None:
        """Adjust the ledger by the difference between the billed and the reserved characters."""
        self._correct(reservation, actual.amount - reservation.usage.amount)

    def refund(self, reservation: UsageReservation) -> None:
        """Give back the reservation of a call that billed nothing."""
        self._correct(reservation, -reservation.usage.amount)

    def exhaust(self) -> None:
        """Tell the ledger the month's characters are used up."""
        self._guard.exhaust(CHARACTER_RESOURCE)

    def remaining(self) -> float | None:
        """Return what the ledger has left this month, or ``None`` when it cannot be read."""
        return self._guard.remaining(CHARACTER_RESOURCE).remaining

    def _granted(self, usage: Usage, model: str, answer: Reserved) -> UsageReservation | UsageDenied:
        if answer.ledger_unavailable:
            return UsageDenied("ledger_unavailable")
        if not answer.granted:
            return UsageDenied("ledger")
        self._used += usage.amount
        return UsageReservation(usage, model, ledgered=True)

    def _correct(self, reservation: UsageReservation, delta: float) -> None:
        if delta == 0:
            return
        with self._lock:
            self._used += delta
            self._guard.adjust(CHARACTER_RESOURCE, delta)
