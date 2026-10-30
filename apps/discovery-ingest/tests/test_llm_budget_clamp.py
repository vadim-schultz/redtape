"""NeuronMeter: a ledger denial with neurons left retries once with the remaining amount (chapter E19, loop B)."""

from __future__ import annotations

import httpx
import pytest
from discovery_ingest.extract.llm.client import LlmResult
from discovery_ingest.extract.llm.meter import Denied, LedgerUnavailable, NeuronMeter, Reservation
from discovery_ingest.extract.llm.prices import estimate

from ledger_fakes import FakeLedger, guard_for

MODEL = "@cf/meta/llama-3.1-8b-instruct"
ESTIMATE = estimate(MODEL, 3000, 1000)
LEFT = ESTIMATE - 50


class _DropsAfterDenial(FakeLedger):
    """A ledger that answers the first denial and then stops answering."""

    def _reserve(self, amount: float) -> httpx.Response:
        response = super()._reserve(amount)
        self.down = response.status_code == 409
        return response


def _meter(monkeypatch: pytest.MonkeyPatch, ledger: FakeLedger) -> NeuronMeter:
    return NeuronMeter(guard_for(monkeypatch, ledger), 4000)


def test_a_ledger_denial_with_neurons_left_retries_with_the_remaining_amount_and_grants_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """reserve · the estimate does not fit, the 50-short remainder does: one retry for exactly what is left."""
    ledger = FakeLedger(remaining=LEFT)
    meter = _meter(monkeypatch, ledger)

    granted = meter.reserve(MODEL, 3000, 1000)

    assert granted == Reservation(MODEL, LEFT, ledgered=True)
    assert ledger.calls == [("reserve", {"amount": ESTIMATE}), ("reserve", {"amount": LEFT})]
    assert meter.used_neurons == LEFT and ledger.remaining == 0


def test_the_clamped_reservation_settles_to_the_reported_cost_through_one_adjust_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """settle · the true cost is above the clamped amount: one adjust of the difference, the ledger ends past the cap."""
    ledger = FakeLedger(remaining=LEFT)
    meter = _meter(monkeypatch, ledger)
    reservation = meter.reserve(MODEL, 3000, 1000)
    assert isinstance(reservation, Reservation)

    meter.settle(reservation, LlmResult("{}", 2000, 300, MODEL, neurons=LEFT + 40.0))

    assert ledger.actions() == ["reserve", "reserve", "adjust"]
    assert ledger.calls[-1] == ("adjust", {"delta": pytest.approx(40.0)})
    assert ledger.remaining == pytest.approx(-40.0) and meter.used_neurons == pytest.approx(LEFT + 40.0)


def test_a_ledger_denial_with_no_neurons_left_is_denied_with_ledger_after_one_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """reserve · nothing left to clamp to: Denied('ledger'), no second reserve call, nothing counted."""
    ledger = FakeLedger(remaining=0)
    meter = _meter(monkeypatch, ledger)

    assert meter.reserve(MODEL, 3000, 1000) == Denied("ledger")
    assert ledger.actions() == ["reserve"] and meter.used_neurons == 0


def test_an_exhausted_day_is_denied_on_both_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    """reserve · the ledger says exhausted: the retry with the remaining amount is refused too, Denied('ledger')."""
    ledger = FakeLedger(remaining=LEFT, exhausted=True)
    meter = _meter(monkeypatch, ledger)

    assert meter.reserve(MODEL, 3000, 1000) == Denied("ledger")
    assert ledger.actions() == ["reserve", "reserve"] and meter.used_neurons == 0


def test_a_ledger_outage_on_the_first_attempt_returns_ledger_unavailable_without_a_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """reserve · a silent ledger is LedgerUnavailable, not a denial, and nothing is counted."""
    ledger = FakeLedger(remaining=LEFT, down=True)
    meter = _meter(monkeypatch, ledger)

    assert meter.reserve(MODEL, 3000, 1000) == LedgerUnavailable()
    assert meter.used_neurons == 0 and meter.ledger_unavailable is True


def test_a_ledger_outage_on_the_second_attempt_returns_ledger_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """reserve · the ledger denies, then stops answering during the retry: LedgerUnavailable, nothing counted."""
    ledger = _DropsAfterDenial(remaining=LEFT)
    meter = _meter(monkeypatch, ledger)

    assert meter.reserve(MODEL, 3000, 1000) == LedgerUnavailable()
    assert meter.used_neurons == 0 and meter.ledger_unavailable is True


def test_refund_of_a_clamped_reservation_gives_back_only_what_was_reserved(monkeypatch: pytest.MonkeyPatch) -> None:
    """refund · the ledger gets minus the clamped amount, not minus the estimate; the day is as it was."""
    ledger = FakeLedger(remaining=LEFT)
    meter = _meter(monkeypatch, ledger)
    reservation = meter.reserve(MODEL, 3000, 1000)
    assert isinstance(reservation, Reservation)

    meter.refund(reservation)

    assert ledger.calls[-1] == ("adjust", {"delta": -LEFT})
    assert ledger.remaining == LEFT and meter.used_neurons == 0
