"""The meter of the Claude Code allowance: nothing reserved, nothing refused, the tokens counted for the report (search-first C19)."""

from __future__ import annotations

from discovery_ingest.translation.meter import UsageReservation
from discovery_ingest.translation.subscription_meter import SubscriptionMeter
from discovery_ingest.translation.units import Usage


def test_the_subscription_meter_grants_every_reservation_and_counts_the_settled_tokens() -> None:
    """meter · a reservation is always granted, is never on the neuron ledger, and the settled tokens are what is reported."""
    meter = SubscriptionMeter()

    reservation = meter.reserve(Usage("subscription", 500.0), "claude-sonnet-5-5")

    assert isinstance(reservation, UsageReservation) and reservation.ledgered is False
    meter.settle(reservation, Usage("subscription", 1300.0))
    meter.refund(reservation)
    assert (meter.used, meter.remaining()) == (1300.0, None)


def test_the_subscription_meter_adds_up_the_tokens_of_several_calls() -> None:
    """meter · the tokens of every answered call add up; a refused call settles nothing."""
    meter = SubscriptionMeter()
    for amount in (100.0, 250.0):
        meter.settle(
            UsageReservation(Usage("subscription", amount), "m", ledgered=False), Usage("subscription", amount)
        )

    assert meter.used == 350.0
