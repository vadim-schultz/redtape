"""The meter of a Claude Code allowance: nothing is reserved or refused here, and the tokens of answered calls are counted.

The CLI enforces the allowance itself: a usage limit comes back as a quota stop, not as a budget the drain can see. So the
meter never touches the neuron ledger and never denies a call; it only adds up what the report shows.
"""

from __future__ import annotations

import threading

from discovery_ingest.translation.meter import UsageReservation
from discovery_ingest.translation.units import Usage


class SubscriptionMeter:
    """A :class:`~discovery_ingest.translation.meter.UsageMeter` for the ``subscription`` unit, safe to share between calls."""

    def __init__(self) -> None:
        """Start at zero tokens with no exhaustion recorded."""
        self._lock = threading.Lock()
        self._tokens = 0.0
        self.exhausted = False

    @property
    def used(self) -> float:
        """The tokens of the calls answered so far."""
        with self._lock:
            return self._tokens

    def reserve(self, usage: Usage, model: str) -> UsageReservation:
        """Grant the reservation: no budget applies and the neuron ledger is not involved."""
        return UsageReservation(usage, model, ledgered=False)

    def settle(self, reservation: UsageReservation, actual: Usage) -> None:
        """Count the tokens the answered call used."""
        with self._lock:
            self._tokens += actual.amount

    def refund(self, reservation: UsageReservation) -> None:
        """Nothing is counted for a refused call, so there is nothing to give back."""

    def exhaust(self) -> None:
        """Record that the CLI reported the allowance used up."""
        self.exhausted = True

    def remaining(self) -> float | None:
        """Report None: the allowance is not visible to the drain, so the amount left is unknown."""
        return None
