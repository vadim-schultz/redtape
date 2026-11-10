"""embed meter: reserve before the call, settle to the usage the provider reported, refund a refused call (search-first C6)."""

from __future__ import annotations

import math

import pytest
from discovery_ingest.budget import BudgetGuard
from discovery_ingest.extract.embedding.client import EmbeddingResult
from discovery_ingest.extract.embedding.meter import EmbeddingMeter, open_embedding_meter
from discovery_ingest.extract.llm.meter import Denied, Reservation
from discovery_ingest.extract.llm.prices import UnknownModelError, embedding_cost, estimate_embedding

from embed_fakes import DIMENSION, MODEL
from ledger_fakes import FakeLedger, guard_for

TEXTS = ["x" * 1500, "y" * 1500]
"""3,000 characters: about 1,000 tokens by the characters-per-token estimate."""


def _result(*, tokens: int | None, neurons: float | None) -> EmbeddingResult:
    return EmbeddingResult(((0.0,) * DIMENSION,) * 2, DIMENSION, MODEL, tokens, neurons, 5)


def _meter(monkeypatch: pytest.MonkeyPatch, ledger: FakeLedger, *, budget: float = 1000.0) -> EmbeddingMeter:
    guard: BudgetGuard = guard_for(monkeypatch, ledger)
    meter = open_embedding_meter(budget, guard, MODEL)
    assert meter is not None
    return meter


def _reserve(meter: EmbeddingMeter) -> Reservation:
    reservation = meter.reserve(TEXTS)
    assert isinstance(reservation, Reservation)
    return reservation


def test_the_price_of_the_model_gives_the_estimate_and_the_priced_tokens() -> None:
    """embed meter · 1,075 neurons per million input tokens; the estimate is characters / 3, rounded up."""
    assert estimate_embedding(MODEL, 3000) == math.ceil(1000 * 1075 / 1e6)
    assert embedding_cost(MODEL, 2000) == pytest.approx(2.15)
    with pytest.raises(UnknownModelError, match="mystery"):
        estimate_embedding("@cf/acme/mystery", 3000)


def test_it_reserves_before_the_call_and_settles_to_the_reported_neurons(monkeypatch: pytest.MonkeyPatch) -> None:
    """embed meter · reserves before and settles to actual usage: the ledger is charged the settled amount."""
    ledger = FakeLedger(9000.0)
    meter = _meter(monkeypatch, ledger)

    reservation = _reserve(meter)
    assert ledger.actions()[-1] == "reserve" and ledger.remaining == 9000.0 - estimate_embedding(MODEL, 3000)
    meter.settle(reservation, _result(tokens=1100, neurons=0.5))

    assert ledger.actions()[-2:] == ["reserve", "adjust"]
    assert ledger.remaining == pytest.approx(9000.0 - 0.5) and meter.used_neurons == pytest.approx(0.5)


def test_it_prices_the_tokens_when_no_neurons_are_reported_and_keeps_the_reservation_without_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """embed meter · tokens are priced from the table; an answer with no usage at all keeps the conservative reservation."""
    ledger = FakeLedger(9000.0)
    meter = _meter(monkeypatch, ledger)

    meter.settle(_reserve(meter), _result(tokens=2000, neurons=None))
    assert ledger.remaining == pytest.approx(9000.0 - 2.15)

    before = ledger.remaining
    meter.settle(_reserve(meter), _result(tokens=None, neurons=None))
    assert ledger.remaining == before - estimate_embedding(MODEL, 3000)


def test_a_refused_call_is_refunded_in_full(monkeypatch: pytest.MonkeyPatch) -> None:
    """embed meter · a refund gives the reservation back to the run and to the ledger."""
    ledger = FakeLedger(9000.0)
    meter = _meter(monkeypatch, ledger)

    meter.refund(_reserve(meter))

    assert ledger.remaining == 9000.0 and meter.used_neurons == 0.0


def test_a_ledger_that_refuses_the_reservation_is_a_denial_and_charges_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """embed meter · a refused reservation is a denial (the drain stops llm_budget) and nothing is charged."""
    ledger = FakeLedger(9000.0)
    meter = _meter(monkeypatch, ledger)
    ledger.exhausted = True

    assert meter.reserve(TEXTS) == Denied("ledger") and meter.used_neurons == 0.0


def test_a_reached_run_budget_is_a_denial(monkeypatch: pytest.MonkeyPatch) -> None:
    """embed meter · once the run's neurons are used up the next reservation is denied."""
    meter = _meter(monkeypatch, FakeLedger(9000.0), budget=1.0)
    meter.settle(_reserve(meter), _result(tokens=None, neurons=4.0))

    assert meter.reserve(TEXTS) == Denied("run_budget")


def test_an_unreachable_ledger_after_the_start_is_retried_on_the_run_budget_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """embed meter · a ledger that fails mid-run is reported unavailable and the run budget carries on."""
    ledger = FakeLedger(9000.0)
    meter = _meter(monkeypatch, ledger)
    ledger.down = True

    reservation = _reserve(meter)

    assert reservation.ledgered is False and meter.ledger_unavailable is True


def test_no_meter_opens_for_an_exhausted_or_unknown_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """embed meter · an exhausted ledger opens no meter; a model without a price is refused at open."""
    guard = guard_for(monkeypatch, FakeLedger(9000.0, exhausted=True))
    assert open_embedding_meter(1000.0, guard, MODEL) is None

    with pytest.raises(UnknownModelError):
        open_embedding_meter(1000.0, guard_for(monkeypatch, FakeLedger(9000.0)), "@cf/acme/mystery")
