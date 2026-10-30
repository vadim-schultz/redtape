"""NeuronMeter: give a reservation back, and fall back to the run budget when the ledger goes away (chapter E6)."""

from __future__ import annotations

import pytest
from discovery_ingest.extract.llm.meter import Denied, LedgerUnavailable, NeuronMeter, Reservation
from discovery_ingest.extract.llm.prices import estimate

from ledger_fakes import FakeLedger, guard_for

MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
ESTIMATE = estimate(MODEL, 3000, 1000)


def _reserved(meter: NeuronMeter) -> Reservation:
    reservation = meter.reserve(MODEL, 3000, 1000)
    assert isinstance(reservation, Reservation)
    return reservation


def test_refund_returns_a_ledgered_reservation_to_the_ledger_and_the_run_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """refund · the ledger gets -estimate and the run total goes back to what it was."""
    ledger = FakeLedger(remaining=9000)
    meter = NeuronMeter(guard_for(monkeypatch, ledger), 4000)
    reservation = _reserved(meter)

    meter.refund(reservation)

    assert ledger.calls[-1] == ("adjust", {"delta": -ESTIMATE})
    assert meter.used_neurons == 0 and ledger.remaining == 9000


def test_refund_of_an_unledgered_reservation_leaves_the_ledger_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    """refund · a reservation only the run budget stood behind never touches the ledger."""
    ledger = FakeLedger(remaining=9000)
    meter = NeuronMeter(guard_for(monkeypatch, ledger), 4000, use_ledger=False)
    reservation = _reserved(meter)

    meter.refund(reservation)

    assert ledger.calls == [] and meter.used_neurons == 0


def test_after_an_outage_the_meter_can_fall_back_to_the_run_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    """stop_using_ledger · the next reservation is granted on the run budget alone and the outage stays reported."""
    ledger = FakeLedger(remaining=9000)
    meter = NeuronMeter(guard_for(monkeypatch, ledger), 4000)
    ledger.down = True
    assert meter.reserve(MODEL, 3000, 1000) == LedgerUnavailable()

    meter.stop_using_ledger()

    assert meter.reserve(MODEL, 3000, 1000) == Reservation(MODEL, ESTIMATE, ledgered=False)
    assert meter.ledger_unavailable is True


def test_the_run_budget_still_stops_a_meter_that_fell_back_after_one_overshooting_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """stop_using_ledger · without the ledger the run budget alone says no, once the last call has passed it."""
    meter = NeuronMeter(guard_for(monkeypatch, FakeLedger(remaining=9000)), ESTIMATE - 1)

    meter.stop_using_ledger()

    assert meter.reserve(MODEL, 3000, 1000) == Reservation(MODEL, ESTIMATE, ledgered=False)
    assert meter.reserve(MODEL, 3000, 1000) == Denied("run_budget")
