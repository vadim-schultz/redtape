"""translate drain: claim, translate per locale, validate, repair once, complete; every limit and error maps to a stop or an outcome (search-first C15)."""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping

import httpx
import pytest
from discovery_ingest.operations.translate_drain import TranslateOptions, run_translate
from discovery_ingest.schemas import DrainReport
from discovery_ingest.translation.adapters.cloudflare_llm import LlmTranslator
from discovery_ingest.translation.engine import TranslationEngine
from discovery_ingest.translation.errors import (
    PermanentError,
    QuotaExceeded,
    RateLimited,
    TransientError,
    Unauthorised,
)
from discovery_ingest.translation.locale_codes import (
    DEFAULT_TARGET_LOCALES,
    register_locale_map,
    unregister_locale_map,
)
from discovery_ingest.translation.meter import NoMeterForUnitError, UsageMeter
from discovery_ingest.translation.registry import register_engine, unregister_engine
from discovery_ingest.translation.settings import TranslationSettings
from discovery_ingest.translation.units import TranslationBatch, TranslationOutcome, UsageUnit
from discovery_ingest.worker.policy import DrainPolicy
from discovery_ingest.worker.translate_drain import TranslateDeps, run_translate_drain

from ledger_fakes import FakeLedger
from llm_transport import ACCOUNT_ID, TOKEN, client, failure, success
from llm_transport import MODEL as LLM_MODEL
from translate_fakes import API_KEY, ENGINE_NAME, MODEL, ScriptedEngine, TranslateApi, task, task_id
from translation_fakes import RecordingMeter


def _drain(
    api: TranslateApi,
    engine: TranslationEngine,
    *,
    max_tasks: int = 10,
    max_batches: int = 10,
    reserve: float = 0.0,
    own_meters: Mapping[UsageUnit, UsageMeter] | None = None,
) -> DrainReport:
    policy = DrainPolicy(max_tasks=max_tasks, max_batches=max_batches, neuron_budget=1000.0)
    deps = TranslateDeps(api.client(), engine, reserve=reserve, own_meters=own_meters or {})
    return run_translate_drain(deps, policy)


def _ids(*numbers: int) -> list[str]:
    return [task_id(number) for number in numbers]


def _mixed() -> list[dict[str, str]]:
    """Six tasks as the queue hands them out: candidates together, locales interleaved."""
    return [task(number, "en" if number % 2 == 0 else "tr") for number in range(6)]


def test_claims_translates_per_locale_validates_and_completes_with_the_report_counts() -> None:
    """translate drain · claims, translates per locale, validates and completes with report counts."""
    api = TranslateApi(_mixed())
    engine = ScriptedEngine()

    report = _drain(api, engine, max_batches=1)

    assert [(b.target_locale, [u.key for u in b.units]) for b in engine.batches] == [
        ("en", _ids(0, 2, 4)),
        ("tr", _ids(1, 3, 5)),
    ]
    assert engine.batches[0].source_locale == "de" and engine.batches[0].glossary.terms
    first = api.posted()[0]
    assert first == {
        "task_id": task_id(0),
        "source_hash": "hash-0",
        "title": "[en] Reisepass beantragen 0",
        "description": "[en] Der Reisepass kostet 60 Euro, Fall 0.",
        "engine": ENGINE_NAME,
        "model": MODEL,
    }
    assert [item["task_id"] for item in api.posted()] == _ids(0, 2, 4, 1, 3, 5)
    assert (report.batches, report.claimed, report.completed, report.failed) == (1, 6, 6, 0)
    assert (report.stop_reason, report.succeeded, report.llm_calls, report.repaired) == ("batch_limit", True, 2, 0)


def test_a_failing_unit_is_repaired_once_and_then_stored() -> None:
    """translate drain · a failing unit is repaired once and then stored; units that passed are not asked again."""
    api = TranslateApi([task(number) for number in range(3)])
    engine = ScriptedEngine(broken=[1])

    report = _drain(api, engine, max_batches=1)

    assert [len(batch.units) for batch in engine.batches] == [3, 1]
    assert engine.batches[1].corrections[0].key == task_id(1)
    assert "numbers not preserved" in engine.batches[1].corrections[0].problems[0]
    posted = {item["task_id"]: item for item in api.posted()}
    assert set(posted) == set(_ids(0, 1, 2)) and posted[task_id(1)]["title"].endswith("beantragen 1")
    assert (report.completed, report.failed, report.repaired, report.invalid, report.llm_calls) == (3, 0, 1, 0, 2)
    assert not api.bodies["fail"]


def test_stored_and_stale_outcomes_are_both_counted_and_nothing_is_retried() -> None:
    """translate drain · stored and stale outcomes are both counted; a stale task is not failed or released."""
    api = TranslateApi([task(number) for number in range(3)])
    api.outcomes[task_id(1)] = ("stale", None)

    report = _drain(api, ScriptedEngine(), max_batches=1)

    assert (report.completed, report.stale, report.failed, report.released) == (3, 1, 0, 0)
    assert not api.bodies["fail"] and not api.bodies["release"]


def test_a_rejected_item_is_logged_and_counted_without_stopping(capsys: pytest.CaptureFixture[str]) -> None:
    """translate drain · a rejected result (a replayed complete, a human row) is logged with its reason, never fatal."""
    api = TranslateApi([task(number) for number in range(3)])
    api.outcomes[task_id(0)] = ("rejected", "task is not claimed by this key")

    report = _drain(api, ScriptedEngine(), max_batches=1)

    assert (report.completed, report.rejected, report.failed, report.succeeded) == (2, 1, 1, True)
    assert "task is not claimed by this key" in capsys.readouterr().err


def test_stops_with_queue_empty_after_the_last_claim_returns_nothing() -> None:
    """translate drain · stops with queue_empty, with no engine call and no reservation for an empty queue."""
    api = TranslateApi([task(number) for number in range(3)])

    report = _drain(api, ScriptedEngine(), max_tasks=2)

    assert (report.stop_reason, report.batches, report.claimed, report.completed) == ("queue_empty", 3, 3, 3)

    empty, engine = TranslateApi([]), ScriptedEngine()
    idle = _drain(empty, engine)

    assert (idle.stop_reason, idle.claimed, idle.neurons_used) == ("queue_empty", 0, 0.0)
    assert engine.batches == [] and "reserve" not in empty.ledger.actions()


class _Snapshot(ScriptedEngine):
    """An engine that notes which ledger calls had happened when it was called."""

    def __init__(self, api: TranslateApi) -> None:
        super().__init__()
        self.api = api
        self.before_call: list[str] = []

    def translate(self, batch: TranslationBatch) -> TranslationOutcome:
        self.before_call = self.api.ledger.actions()
        return super().translate(batch)


def test_the_meter_reserves_before_the_call_and_settles_to_the_reported_usage() -> None:
    """translate drain · meter reserves before and settles to usage: 8 reserved, 6 spent, the day charged 6."""
    api = TranslateApi([task(number) for number in range(3)])
    engine = _Snapshot(api)

    report = _drain(api, engine, max_batches=1)

    assert "reserve" in engine.before_call and "adjust" not in engine.before_call
    reserve = next(body for action, body in api.ledger.calls if action == "reserve")
    assert reserve["amount"] == 8
    assert api.ledger.remaining == pytest.approx(9000 - 6) and report.neurons_used == pytest.approx(6.0)


def test_a_reservation_that_would_take_the_ledger_below_the_floor_stops_with_llm_budget_and_releases() -> None:
    """translate drain · stops with llm_budget when the reserved query-embedding floor would be breached."""
    api = TranslateApi([task(number) for number in range(3)], ledger=FakeLedger(905.0))
    engine = ScriptedEngine()

    report = _drain(api, engine, reserve=900.0)

    assert (report.stop_reason, report.succeeded, report.claimed, report.released) == ("llm_budget", True, 3, 3)
    assert engine.batches == [] and "reserve" not in api.ledger.actions() and api.ledger.remaining == 905.0
    assert api.bodies["release"][0]["task_ids"] == _ids(0, 1, 2) and not api.bodies["fail"]


def test_the_floor_holds_after_earlier_batches_and_the_ledger_never_ends_below_it() -> None:
    """translate drain · the floor is checked per batch: two batches fit, the third would breach it and is released."""
    api = TranslateApi([task(number) for number in range(6)], ledger=FakeLedger(912.0))

    report = _drain(api, ScriptedEngine(), max_tasks=2, reserve=900.0)

    assert (report.stop_reason, report.completed, report.released) == ("llm_budget", 4, 2)
    assert api.ledger.remaining >= 900.0


def test_a_ledger_that_cannot_prove_the_floor_stops_with_llm_budget() -> None:
    """translate drain · with the floor unverifiable (ledger down) the drain claims nothing and spends nothing."""
    api = TranslateApi([task(0)], ledger=FakeLedger(5000.0, down=True))
    engine = ScriptedEngine()

    report = _drain(api, engine, reserve=900.0)

    assert (report.stop_reason, report.claimed, report.ledger_unavailable) == ("llm_budget", 0, True)
    assert engine.batches == [] and not api.bodies["claim"]


def test_a_ledger_at_or_below_the_floor_stops_before_claiming_anything() -> None:
    """translate drain · nothing above the floor today: llm_budget before any claim."""
    api = TranslateApi([task(0)], ledger=FakeLedger(900.0))

    report = _drain(api, ScriptedEngine(), reserve=900.0)

    assert (report.stop_reason, report.claimed) == ("llm_budget", 0) and not api.bodies["claim"]


def test_an_engine_billed_in_another_unit_uses_its_own_meter_and_skips_the_floor() -> None:
    """translate drain · a non-neuron engine is metered by its own meter; the neuron ledger and floor are untouched."""
    api = TranslateApi([task(number) for number in range(3)], ledger=FakeLedger(10.0))
    meter = RecordingMeter()
    engine = ScriptedEngine(unit="characters", neurons=40.0)

    report = _drain(api, engine, reserve=5000.0, own_meters={"characters": meter})

    assert (report.completed, report.stop_reason, report.neurons_used) == (3, "queue_empty", 0.0)
    assert [usage.unit for usage in meter.reserved] == ["characters"] and meter.settled[0].amount == 120.0
    assert api.ledger.calls == []


def test_quota_exhaustion_stops_with_llm_quota_and_releases_what_was_not_translated() -> None:
    """translate drain · quota stops with llm_quota; finished locales stay stored, the rest is released, no attempt burned."""
    api = TranslateApi(_mixed())

    class Quota(ScriptedEngine):
        def translate(self, batch: TranslationBatch) -> TranslationOutcome:
            if batch.target_locale == "tr":
                raise QuotaExceeded("daily free allocation used up")
            return super().translate(batch)

    report = _drain(api, Quota(), max_batches=1)

    assert (report.stop_reason, report.succeeded, report.completed, report.released) == ("llm_quota", True, 3, 3)
    assert api.bodies["release"][0]["task_ids"] == _ids(1, 3, 5) and "llm_quota" in api.bodies["release"][0]["reason"]
    assert not api.bodies["fail"] and "exhaust" in api.ledger.actions()


def test_a_rate_limited_batch_releases_its_tasks_without_an_attempt_and_stops_the_drain() -> None:
    """translate drain · a 429 releases the open tasks without an attempt, stops rate_limited, and the next claim never runs."""
    api = TranslateApi(_mixed())

    class Limited(ScriptedEngine):
        def translate(self, batch: TranslationBatch) -> TranslationOutcome:
            if batch.target_locale == "tr":
                raise RateLimited("429000: slow down", retry_after=5.0)
            return super().translate(batch)

    report = _drain(api, Limited(), max_batches=3)

    assert (report.stop_reason, report.succeeded, report.completed, report.released) == ("rate_limited", True, 3, 3)
    assert not api.bodies["fail"] and api.bodies["release"][0]["task_ids"] == _ids(1, 3, 5)
    assert len(api.bodies["claim"]) == 1


def test_an_unavailable_item_ends_the_drain_cleanly_and_the_unstarted_locales_are_released() -> None:
    """translate drain · an unavailable item (object store down) stops without a loop; the rest of the batch goes back."""
    api = TranslateApi(_mixed())
    api.outcomes[task_id(2)] = ("unavailable", "object store is not configured")
    engine = ScriptedEngine()

    report = _drain(api, engine)

    assert (report.stop_reason, report.succeeded, report.unavailable) == ("storage_unavailable", True, 1)
    assert len(api.bodies["claim"]) == 1 and [b.target_locale for b in engine.batches] == ["en"]
    assert api.bodies["release"][0]["task_ids"] == _ids(1, 3, 5)
    assert (report.completed, report.released) == (2, 3) and not api.bodies["fail"]


def test_a_unit_that_still_fails_validation_after_the_repair_is_failed_for_good_and_never_stored() -> None:
    """translate drain · a still-invalid unit is failed non-retryably with the reason and never posted."""
    api = TranslateApi([task(number) for number in range(3)])
    engine = ScriptedEngine(stubborn=[1])

    report = _drain(api, engine, max_batches=1)

    (fail,) = api.bodies["fail"]
    assert fail["task_id"] == task_id(1) and fail["retryable"] is False
    assert "validation failed after one repair" in fail["error"] and "numbers not preserved" in fail["error"]
    assert [item["task_id"] for item in api.posted()] == _ids(0, 2)
    assert (report.completed, report.failed, report.invalid, report.repaired) == (2, 1, 1, 0)
    assert len(engine.batches) == 2


@pytest.mark.parametrize(
    ("error", "retryable"), [(TransientError("provider answered 503"), True), (PermanentError("bad request"), False)]
)
def test_an_engine_error_fails_the_batch_tasks_and_the_drain_goes_on(error: Exception, retryable: bool) -> None:
    """translate drain · a 5xx fails the batch retryably (a rejection permanently) and the next batch still runs."""
    api = TranslateApi([task(number) for number in range(4)])
    engine = ScriptedEngine(error, None)  # type: ignore[arg-type]

    report = _drain(api, engine, max_tasks=2)

    fails = api.bodies["fail"]
    assert [body["task_id"] for body in fails] == _ids(0, 1) and {body["retryable"] for body in fails} == {retryable}
    assert (report.failed, report.completed, report.succeeded, report.stop_reason) == (2, 2, True, "queue_empty")
    assert api.ledger.remaining == pytest.approx(9000 - 4.0)


def test_a_rejected_token_stops_as_infrastructure_and_releases_the_batch() -> None:
    """translate drain · a 401 stops with error (succeeded false), releases the batch and fails nothing."""
    api = TranslateApi([task(number) for number in range(2)])

    report = _drain(api, ScriptedEngine(Unauthorised("authentication error")))

    assert (report.stop_reason, report.succeeded, report.released) == ("error", False, 2)
    assert report.error is not None and "credentials" in report.error and not api.bodies["fail"]


def test_the_database_soft_limit_on_complete_stops_with_db_limit_and_releases_the_batch() -> None:
    """translate drain · the 507 soft limit on complete stops with db_limit and releases the batch."""
    api = TranslateApi([task(number) for number in range(2)])
    api.forced["complete"] = (507, "database_soft_limit")

    report = _drain(api, ScriptedEngine())

    assert (report.stop_reason, report.succeeded, report.released, report.completed) == ("db_limit", True, 2, 0)
    assert not api.bodies["fail"]


def test_the_database_soft_limit_on_claim_stops_with_db_limit() -> None:
    """translate drain · the 507 soft limit on claim stops with db_limit having claimed nothing."""
    api = TranslateApi([task(0)])
    api.forced["claim"] = (507, "database_soft_limit")

    report = _drain(api, ScriptedEngine())

    assert (report.stop_reason, report.claimed, report.succeeded) == ("db_limit", 0, True)


@pytest.mark.parametrize("route", ["claim", "complete", "fail"])
def test_a_transport_failure_stops_as_error_releases_the_batch_and_still_reports(route: str) -> None:
    """translate drain · a timeout (outcome unknown) is a stop with a report, never a traceback; the batch goes back."""
    api = TranslateApi([task(number) for number in range(2)])
    api.unreachable.add(route)
    engine = ScriptedEngine(TransientError("503")) if route == "fail" else ScriptedEngine()

    report = _drain(api, engine)

    assert (report.stop_reason, report.succeeded) == ("error", False)
    assert report.error is not None and "ReadTimeout" in report.error
    assert report.released == (0 if route == "claim" else 2)


def test_a_conflict_on_fail_and_on_release_is_not_fatal() -> None:
    """translate drain · fail and release answer 409 for a task this key does not hold: counted skipped, never raised."""
    api = TranslateApi([task(number) for number in range(2)])
    api.forced["fail"] = (409, "task is not claimed by this key")

    report = _drain(api, ScriptedEngine(TransientError("503")), max_batches=1)

    assert (report.failed, report.skipped, report.succeeded) == (0, 2, True)

    api = TranslateApi([task(number) for number in range(2)])
    api.forced["release"] = (409, "task is not claimed by this key")

    report = _drain(api, ScriptedEngine(QuotaExceeded("used up")))

    assert (report.stop_reason, report.released, report.succeeded) == ("llm_quota", 0, True)


def test_a_short_response_fails_the_whole_batch_and_posts_nothing() -> None:
    """translate drain · fewer results than units fails the batch retryably; no item is silently dropped or stored."""
    api = TranslateApi([task(number) for number in range(3)])

    report = _drain(api, ScriptedEngine(short=True), max_batches=1)

    assert [body["task_id"] for body in api.bodies["fail"]] == _ids(0, 1, 2)
    assert {body["retryable"] for body in api.bodies["fail"]} == {True}
    assert not api.bodies["complete"] and (report.failed, report.completed) == (3, 0)


def _cloudflare_answer(request: httpx.Request, *, drop: int = 0) -> httpx.Response:
    units = json.loads(json.loads(request.content)["messages"][-1]["content"])["units"]
    kept = units[: len(units) - drop]
    answer = {
        "units": [
            {"key": u["key"], "title": f"[en] {u['title']}", "description": f"[en] {u['description']}"} for u in kept
        ]
    }
    return success(answer, {"prompt_tokens": 100, "completion_tokens": 60, "neurons": 3.0})


def test_a_short_model_answer_through_the_workers_ai_adapter_fails_the_batch_retryably() -> None:
    """translate drain · the real adapter's short answer (one unit missing) fails the batch, nothing is dropped."""
    api = TranslateApi([task(number) for number in range(3)])
    engine = LlmTranslator(
        client(lambda request: _cloudflare_answer(request, drop=1)), model=LLM_MODEL, max_tokens=2000
    )

    report = _drain(api, engine, max_batches=1)

    assert (report.failed, report.completed) == (3, 0) and not api.bodies["complete"]
    assert {body["retryable"] for body in api.bodies["fail"]} == {True}


def test_secrets_never_reach_the_report_the_failures_or_the_log(capsys: pytest.CaptureFixture[str]) -> None:
    """secrets · neither the Workers AI token, the account id nor the API key appears in a report, a failure or stderr."""
    api = TranslateApi([task(0)])
    denied = LlmTranslator(
        client(lambda _r: failure(401, 10000, f"Authentication error {TOKEN} {ACCOUNT_ID}")),
        model=LLM_MODEL,
        max_tokens=2000,
    )
    auth_report = _drain(api, denied)

    api = TranslateApi([task(0)])
    rejected = LlmTranslator(
        client(lambda _r: failure(400, 5006, f"bad request {TOKEN} {ACCOUNT_ID}")), model=LLM_MODEL, max_tokens=2000
    )
    failed_report = _drain(api, rejected, max_batches=1)
    fail_bodies = api.bodies["fail"]

    api = TranslateApi([task(0)])
    api.forced["complete"] = (500, f"upstream echoed {API_KEY}")
    api_report = _drain(api, ScriptedEngine())

    everything = [r.model_dump_json() for r in (auth_report, failed_report, api_report)]
    everything += [str(fail_bodies), capsys.readouterr().err]
    for text in everything:
        assert TOKEN not in text and ACCOUNT_ID not in text and API_KEY not in text
    assert fail_bodies and failed_report.failed == 1


def test_a_neuron_drain_without_a_neuron_budget_is_refused() -> None:
    """translate drain · a neuron-billed drain without a run budget raises before anything is claimed."""
    api = TranslateApi([task(0)])

    with pytest.raises(ValueError, match="neuron_budget"):
        run_translate_drain(TranslateDeps(api.client(), ScriptedEngine()), DrainPolicy(max_tasks=1))

    assert not api.bodies["claim"]


def test_an_unavailable_queue_summary_is_reported_as_unknown_not_as_a_failure() -> None:
    """translate drain · a summary that cannot be read leaves remaining unknown; the drain still succeeded."""
    api = TranslateApi([])
    api.forced["summary"] = (500, "boom")

    report = _drain(api, ScriptedEngine())

    assert (report.remaining, report.remaining_unknown, report.succeeded) == (None, True, True)


@pytest.fixture
def _registered() -> Iterator[None]:
    register_locale_map(ENGINE_NAME, {code: code for code in DEFAULT_TARGET_LOCALES})
    yield
    unregister_engine(ENGINE_NAME)
    unregister_locale_map(ENGINE_NAME)


@pytest.mark.usefixtures("_registered")
def test_the_engine_comes_from_the_registry_and_the_drain_posts_its_name_and_model() -> None:
    """translate drain · builds the engine from the registry and posts its name and model; no provider is named."""
    engine = ScriptedEngine()
    register_engine(ENGINE_NAME, lambda _config: engine)
    api = TranslateApi([task(number) for number in range(2)])
    settings = TranslationSettings.model_validate({"TRANSLATION_ENGINE": ENGINE_NAME})

    report = run_translate(TranslateOptions(max_batches=2), settings, api.client())

    assert {(item["engine"], item["model"]) for item in api.posted()} == {(ENGINE_NAME, MODEL)}
    assert (report.completed, report.stop_reason) == (2, "queue_empty")


def test_an_engine_in_a_unit_with_no_meter_is_refused_before_anything_is_claimed() -> None:
    """translate drain · a characters engine without a meter of its own raises NoMeterForUnitError and claims nothing."""
    api = TranslateApi([task(0)])

    with pytest.raises(NoMeterForUnitError, match="characters"):
        _drain(api, ScriptedEngine(unit="characters"))

    assert not api.bodies["claim"]


class _RacedLedger(FakeLedger):
    """A ledger that another spender (a second drain, a burst of query embeddings) empties just before our reserve."""

    def __init__(self, remaining: float, stolen: float) -> None:
        super().__init__(remaining)
        self.stolen = stolen

    def _reserve(self, amount: float) -> httpx.Response:
        self.remaining -= self.stolen
        self.stolen = 0.0
        return super()._reserve(amount)


def test_a_spender_that_races_the_floor_check_is_caught_and_the_reservation_is_given_back() -> None:
    """translate drain · the floor is verified after the reserve: a racing spender makes the drain refund and stop llm_budget."""
    api = TranslateApi([task(number) for number in range(3)], ledger=_RacedLedger(1000.0, stolen=100.0))
    engine = ScriptedEngine()

    report = _drain(api, engine, reserve=900.0)

    assert (report.stop_reason, report.released, report.succeeded) == ("llm_budget", 3, True)
    assert engine.batches == [] and api.ledger.remaining == 900.0 and "adjust" in api.ledger.actions()
    assert report.neurons_used == 0.0


def test_a_reservation_that_clears_the_floor_after_the_reserve_is_kept() -> None:
    """translate drain · with headroom after the reserve the reservation stands and settles to the real usage."""
    api = TranslateApi([task(number) for number in range(3)], ledger=_RacedLedger(1000.0, stolen=0.0))

    report = _drain(api, ScriptedEngine(), max_batches=1, reserve=900.0)

    assert (report.completed, report.stop_reason) == (3, "batch_limit")
    assert api.ledger.remaining == pytest.approx(1000.0 - 6.0)
