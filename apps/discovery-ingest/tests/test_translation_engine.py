"""The Cloudflare LLM translator and the metered call: results in order, usage in neurons, errors as categories."""

from __future__ import annotations

import json

import httpx
import pytest
from discovery_ingest.extract.llm.prices import UnknownModelError
from discovery_ingest.translation.adapters.cloudflare_llm import LlmTranslator
from discovery_ingest.translation.errors import QuotaExceeded, UnusableOutputError
from discovery_ingest.translation.meter import NeuronUsageMeter, UsageDenied
from discovery_ingest.translation.metered import MeteredTranslator
from discovery_ingest.translation.units import Usage
from discovery_ingest.worker.stop import StopDrain

from ledger_fakes import FakeLedger, guard_for
from llm_transport import MODEL, client, failure, success
from translation_fakes import RecordingMeter, batch, unit

BATCH = batch(unit("a", "Antrag auf Kindergeld", "Bitte reichen Sie den Antrag ein."), unit("b", "Wohngeld", ""))


def _answer(*keys: str) -> dict[str, list[dict[str, str]]]:
    return {"units": [{"key": key, "title": f"T-{key}", "description": f"D-{key}"} for key in keys]}


def _translator(handler: object, *, max_tokens: int = 2000) -> LlmTranslator:
    return LlmTranslator(client(handler), model=MODEL, max_tokens=max_tokens)  # type: ignore[arg-type]


def test_the_translator_returns_one_result_per_unit_in_order_and_reports_neurons() -> None:
    """engine · LlmTranslator returns one result per unit in order and reports usage in neurons."""
    usage = {"prompt_tokens": 500, "completion_tokens": 300, "neurons": 12.5}

    outcome = _translator(lambda _request: success(_answer("b", "a"), usage)).translate(BATCH)

    assert [(r.key, r.title, r.description) for r in outcome.results] == [("a", "T-a", "D-a"), ("b", "T-b", "D-b")]
    assert outcome.usage == Usage("neurons", 12.5)
    assert outcome.model == MODEL


def test_usage_falls_back_to_the_priced_tokens_and_then_to_the_estimate() -> None:
    """engine · without reported neurons the tokens are priced; without tokens the estimate stands."""
    translator = _translator(
        lambda _request: success(_answer("a", "b"), {"prompt_tokens": 1_000_000, "completion_tokens": 0})
    )
    bare = _translator(lambda _request: success(_answer("a", "b")))

    assert translator.translate(BATCH).usage == Usage("neurons", 25_608)
    assert bare.translate(BATCH).usage == bare.estimate(BATCH)


def test_the_request_carries_the_glossary_the_target_language_and_the_units_as_data() -> None:
    """engine · the prompt names the target language, injects glossary renderings and keep terms, and sends units as JSON."""
    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return success(_answer("a", "b"))

    _translator(handler).translate(batch(*BATCH.units, target="tr"))

    body = seen[0]
    system, user = body["messages"][0]["content"], body["messages"][1]["content"]  # type: ignore[index]
    assert "Turkish" in system and "Antrag" in system and "application" in system and "SGB II" in system
    assert json.loads(user)["units"][0] == {
        "key": "a",
        "title": "Antrag auf Kindergeld",
        "description": "Bitte reichen Sie den Antrag ein.",
    }
    assert body["response_format"]["json_schema"]["properties"]["units"]["type"] == "array"  # type: ignore[index]
    assert body["max_tokens"] == 2000


@pytest.mark.parametrize(
    "answer",
    [_answer("a"), _answer("a", "x"), {"units": "nope"}, {"other": []}],
    ids=["short", "wrong-key", "not-a-list", "wrong-shape"],
)
def test_a_response_that_does_not_cover_every_unit_is_an_unusable_output_error(answer: object) -> None:
    """engine · a short or malformed answer raises UnusableOutputError instead of dropping units."""
    with pytest.raises(UnusableOutputError):
        _translator(lambda _request: success(answer)).translate(BATCH)


def test_the_estimate_grows_with_the_batch() -> None:
    """engine · the estimate is in neurons, positive, and larger for a larger batch."""
    translator = _translator(lambda _request: success(_answer()))

    many = batch(
        *(unit(f"k{i}", "Antrag auf Kindergeld" * 5, "Bitte reichen Sie den Antrag ein. " * 8) for i in range(10))
    )
    small, large = translator.estimate(BATCH), translator.estimate(many)

    assert small.unit == large.unit == "neurons"
    assert 0 < small.amount < large.amount


def test_a_quota_error_releases_the_reservation_and_raises_the_stop_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    """engine · a quota error refunds the meter reservation, marks the day exhausted and stops with llm_quota."""
    engine = _translator(lambda _request: failure(429, 4006, "you have used up your daily free allocation"))
    ledger = FakeLedger(remaining=5000)
    meter = NeuronUsageMeter(guard_for(monkeypatch, ledger), run_limit=4000)

    with pytest.raises(StopDrain) as stop:
        MeteredTranslator(engine, meter).translate(BATCH)

    assert stop.value.reason == "llm_quota"
    assert ledger.remaining == 5000 and ledger.exhausted
    assert meter.used == 0


def test_a_successful_call_settles_the_reservation_with_the_reported_neurons(monkeypatch: pytest.MonkeyPatch) -> None:
    """engine · the ledger ends up charged the actual neurons, not the estimate."""
    engine = _translator(lambda _request: success(_answer("a", "b"), {"neurons": 7.0}))
    ledger = FakeLedger(remaining=5000)
    meter = NeuronUsageMeter(guard_for(monkeypatch, ledger), run_limit=4000)

    MeteredTranslator(engine, meter).translate(BATCH)

    assert ledger.remaining == pytest.approx(5000 - 7.0)
    assert meter.used == pytest.approx(7.0)


def test_a_denied_reservation_stops_with_llm_budget_before_any_call() -> None:
    """engine · a meter that denies the estimate stops the drain with llm_budget and the engine is never called."""
    calls: list[int] = []
    engine = _translator(lambda _request: calls.append(1) or success(_answer("a", "b")))

    with pytest.raises(StopDrain) as stop:
        MeteredTranslator(engine, RecordingMeter(deny=UsageDenied("ledger"))).translate(BATCH)

    assert stop.value.reason == "llm_budget" and calls == []


def test_an_unauthorised_error_refunds_and_stops_with_an_error_reason() -> None:
    """engine · rejected credentials refund the reservation and stop the drain as an infrastructure error."""
    meter = RecordingMeter()
    engine = _translator(lambda _request: failure(401, 10000, "authentication error"))

    with pytest.raises(StopDrain) as stop:
        MeteredTranslator(engine, meter).translate(BATCH)

    assert stop.value.reason == "error" and len(meter.refunded) == 1


def test_the_engine_error_for_quota_is_a_translation_error_not_an_llm_error() -> None:
    """engine · the port raises its own categories; Workers AI error classes never leave the adapter."""
    engine = _translator(lambda _request: failure(429, 4006, "you have used up your daily free allocation"))

    with pytest.raises(QuotaExceeded):
        engine.translate(BATCH)


def test_an_unreachable_ledger_falls_back_to_the_run_budget_and_an_exhausted_run_is_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """meter · with the ledger down the reservation is granted against the run budget alone; once it is used up it is denied."""
    meter = NeuronUsageMeter(guard_for(monkeypatch, FakeLedger(remaining=100, down=True)), run_limit=20)

    first = meter.reserve(Usage("neurons", 25), "llm")
    second = meter.reserve(Usage("neurons", 5), "llm")

    assert first.ledgered is False and first.usage == Usage("neurons", 25)  # type: ignore[union-attr]
    assert second == UsageDenied("run_budget")
    assert meter.remaining() == 0.0


def test_a_model_without_a_price_is_refused_rather_than_guessed() -> None:
    """engine · estimating for a model with no neuron price raises UnknownModelError, so the CLI can say which one."""
    translator = LlmTranslator(
        client(lambda _request: success(_answer())), model="@cf/acme/mystery-model", max_tokens=100
    )

    with pytest.raises(UnknownModelError, match="mystery-model"):
        translator.estimate(BATCH)
