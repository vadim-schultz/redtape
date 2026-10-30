"""NeuronMeter: reserve, settle and exhaust through the budget ledger, under the run budget (chapter E4, loop B)."""

from __future__ import annotations

import pytest
from discovery_ingest.extract.llm.client import LlmResult
from discovery_ingest.extract.llm.meter import Denied, LedgerUnavailable, NeuronMeter, Reservation, open_neuron_meter
from discovery_ingest.extract.llm.prices import UnknownModelError, cost, estimate

from ledger_fakes import FakeLedger, guard_for

MODEL = "@cf/meta/llama-3.1-8b-instruct"
ESTIMATE = estimate(MODEL, 3000, 1000)


def _result(input_tokens: int | None, output_tokens: int | None, neurons: float | None = None) -> LlmResult:
    return LlmResult("{}", input_tokens, output_tokens, MODEL, neurons)


def test_reserve_is_granted_within_the_ledger_then_clamped_to_what_is_left_and_then_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """reserve · the ledger grants the estimate while it lasts, then the 5 left, then a denial is Denied, not an exception."""
    ledger = FakeLedger(remaining=ESTIMATE + 5)
    meter = NeuronMeter(guard_for(monkeypatch, ledger), 4000)

    granted = meter.reserve(MODEL, 3000, 1000)
    clamped = meter.reserve(MODEL, 3000, 1000)
    denied = meter.reserve(MODEL, 3000, 1000)

    assert granted == Reservation(MODEL, ESTIMATE, ledgered=True)
    assert clamped == Reservation(MODEL, 5, ledgered=True)
    assert denied == Denied("ledger")
    assert meter.used_neurons == ESTIMATE + 5


def test_a_reservation_that_would_pass_the_run_limit_is_granted_while_used_is_below_the_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """reserve · the estimate crosses the run limit but nothing is used yet: the call may go out (overshoot, X18)."""
    ledger = FakeLedger(remaining=9000)
    meter = NeuronMeter(guard_for(monkeypatch, ledger), ESTIMATE - 1)

    assert meter.reserve(MODEL, 3000, 1000) == Reservation(MODEL, ESTIMATE, ledgered=True)
    assert meter.used_neurons == ESTIMATE


def test_a_reservation_is_denied_with_run_budget_once_used_has_reached_the_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """reserve · used at the limit is Denied('run_budget') and the ledger is never called for it."""
    ledger = FakeLedger(remaining=9000)
    meter = NeuronMeter(guard_for(monkeypatch, ledger), ESTIMATE)
    assert isinstance(meter.reserve(MODEL, 3000, 1000), Reservation)
    ledger.calls.clear()

    assert meter.reserve(MODEL, 3000, 1000) == Denied("run_budget")
    assert ledger.calls == []


def test_after_an_overshooting_call_settles_the_next_reservation_is_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    """reserve · the run stops after one call: a settlement at or above the limit closes the run budget."""
    meter = NeuronMeter(guard_for(monkeypatch, FakeLedger(remaining=9000)), ESTIMATE - 1)
    reservation = meter.reserve(MODEL, 3000, 1000)
    assert isinstance(reservation, Reservation)

    meter.settle(reservation, _result(None, None, neurons=ESTIMATE - 1 + 0.5))

    assert meter.reserve(MODEL, 3000, 1000) == Denied("run_budget")


def test_without_a_ledger_the_run_budget_alone_overshoots_by_one_call_and_then_stops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """reserve · use_ledger false: one call may cross the limit, the next is Denied('run_budget'), no ledger call."""
    ledger = FakeLedger(remaining=9000)
    meter = NeuronMeter(guard_for(monkeypatch, ledger), ESTIMATE - 1, use_ledger=False)

    assert meter.reserve(MODEL, 3000, 1000) == Reservation(MODEL, ESTIMATE, ledgered=False)
    assert meter.reserve(MODEL, 3000, 1000) == Denied("run_budget")
    assert ledger.calls == []


def test_an_unknown_model_is_refused_before_any_ledger_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """reserve · no price, no reservation: UnknownModelError and nothing reserved."""
    ledger = FakeLedger(remaining=9000)
    meter = NeuronMeter(guard_for(monkeypatch, ledger), 4000)

    with pytest.raises(UnknownModelError):
        meter.reserve("@cf/acme/mystery-model", 3000, 1000)

    assert ledger.calls == [] and meter.used_neurons == 0


def test_a_ledger_that_goes_away_mid_run_is_reported_as_ledger_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """reserve · an outage after the meter opened returns LedgerUnavailable; the call must not go out."""
    ledger = FakeLedger(remaining=9000)
    meter = NeuronMeter(guard_for(monkeypatch, ledger), 4000)
    ledger.down = True

    assert meter.reserve(MODEL, 3000, 1000) == LedgerUnavailable()
    assert meter.used_neurons == 0


def test_settle_adjusts_by_actual_minus_reserved(monkeypatch: pytest.MonkeyPatch) -> None:
    """settle · usage present: the ledger gets actual - reserved and the run total follows the real cost."""
    ledger = FakeLedger(remaining=9000)
    meter = NeuronMeter(guard_for(monkeypatch, ledger), 4000)
    reservation = meter.reserve(MODEL, 3000, 1000)
    assert isinstance(reservation, Reservation)

    meter.settle(reservation, _result(2000, 300))

    actual = cost(MODEL, 2000, 300)
    assert ledger.calls[-1] == ("adjust", {"delta": pytest.approx(actual - ESTIMATE)})
    assert meter.used_neurons == pytest.approx(actual)


def test_settle_keeps_the_reservation_when_usage_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """settle · no token counts: no adjust call, the reservation stands (conservative)."""
    ledger = FakeLedger(remaining=9000)
    meter = NeuronMeter(guard_for(monkeypatch, ledger), 4000)
    reservation = meter.reserve(MODEL, 3000, 1000)
    assert isinstance(reservation, Reservation)

    meter.settle(reservation, _result(None, None))

    assert "adjust" not in ledger.actions() and meter.used_neurons == ESTIMATE


def test_settle_uses_the_reported_neurons_when_present_and_the_price_table_otherwise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """settle · the provider's own figure beats the table, even without token counts; without it the table stands."""
    ledger = FakeLedger(remaining=9000)
    meter = NeuronMeter(guard_for(monkeypatch, ledger), 4000)
    first, second = meter.reserve(MODEL, 3000, 1000), meter.reserve(MODEL, 3000, 1000)
    assert isinstance(first, Reservation) and isinstance(second, Reservation)

    meter.settle(first, _result(2000, 300, neurons=12.5))
    assert ledger.calls[-1] == ("adjust", {"delta": pytest.approx(12.5 - ESTIMATE)})
    meter.settle(second, _result(None, None, neurons=7.0))

    assert ledger.calls[-1] == ("adjust", {"delta": pytest.approx(7.0 - ESTIMATE)})
    assert meter.used_neurons == pytest.approx(12.5 + 7.0)


def test_settle_prices_the_tokens_when_no_neurons_were_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    """settle · the table is the fallback: tokens without a reported figure settle at ``cost`` as before."""
    ledger = FakeLedger(remaining=9000)
    meter = NeuronMeter(guard_for(monkeypatch, ledger), 4000)
    reservation = meter.reserve(MODEL, 3000, 1000)
    assert isinstance(reservation, Reservation)

    meter.settle(reservation, _result(2000, 300, neurons=None))

    assert meter.used_neurons == pytest.approx(cost(MODEL, 2000, 300))


def test_a_quota_error_exhausts_the_day_in_the_ledger(monkeypatch: pytest.MonkeyPatch) -> None:
    """exhaust · tells the ledger the day's neurons are gone, so the next reserve is denied."""
    ledger = FakeLedger(remaining=9000)
    meter = NeuronMeter(guard_for(monkeypatch, ledger), 4000)

    meter.exhaust()

    assert ledger.actions() == ["exhaust"]
    assert meter.reserve(MODEL, 3000, 1000) == Denied("ledger")


def test_the_run_budget_is_capped_at_what_the_ledger_has_left(monkeypatch: pytest.MonkeyPatch) -> None:
    """open_neuron_meter · a run budget of 4000 on a day with ESTIMATE + 1 left closes once ESTIMATE + 1 is used."""
    meter = open_neuron_meter(4000, guard_for(monkeypatch, FakeLedger(remaining=ESTIMATE + 1)))
    assert meter is not None
    reservation = meter.reserve(MODEL, 3000, 1000)
    assert isinstance(reservation, Reservation)

    meter.settle(reservation, _result(None, None, neurons=ESTIMATE + 1))

    assert meter.reserve(MODEL, 3000, 1000) == Denied("run_budget")


def test_a_run_budget_smaller_than_the_ledger_lets_one_call_pass_it_and_then_stops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """open_neuron_meter · with limit ESTIMATE + 1 the second call starts below the limit and crosses it; the third stops."""
    meter = open_neuron_meter(ESTIMATE + 1, guard_for(monkeypatch, FakeLedger(remaining=9000)))
    assert meter is not None

    assert isinstance(meter.reserve(MODEL, 3000, 1000), Reservation)
    assert isinstance(meter.reserve(MODEL, 3000, 1000), Reservation)
    assert meter.reserve(MODEL, 3000, 1000) == Denied("run_budget")


def test_an_exhausted_ledger_opens_no_meter(monkeypatch: pytest.MonkeyPatch) -> None:
    """open_neuron_meter · a day already exhausted (or at zero) means the run cannot spend: None."""
    assert open_neuron_meter(4000, guard_for(monkeypatch, FakeLedger(remaining=100, exhausted=True))) is None
    assert open_neuron_meter(4000, guard_for(monkeypatch, FakeLedger(remaining=0))) is None


def test_an_unreachable_ledger_falls_back_to_the_run_budget_and_reports_ledger_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """open_neuron_meter · no ledger: the run budget alone applies, nothing is reserved remotely, and it says so."""
    ledger = FakeLedger(remaining=9000, down=True)
    meter = open_neuron_meter(ESTIMATE + 1, guard_for(monkeypatch, ledger))
    assert meter is not None

    granted = meter.reserve(MODEL, 3000, 1000)
    overshoot = meter.reserve(MODEL, 3000, 1000)
    denied = meter.reserve(MODEL, 3000, 1000)

    assert granted == overshoot == Reservation(MODEL, ESTIMATE, ledgered=False)
    assert denied == Denied("run_budget")
    assert meter.ledger_unavailable is True and ledger.calls == []
