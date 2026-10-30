"""llm_extract limits release the claimed tasks and stop the drain; only page problems fail a task (chapter E6, B)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest
from discovery_ingest.api_client import DiscoveryMachineClient
from discovery_ingest.extract.clean import clean_page
from discovery_ingest.extract.llm.errors import LlmAuthError, LlmQuotaExceeded, LlmRequestError
from discovery_ingest.extract.llm.prices import cost, estimate, reserved_output_tokens
from discovery_ingest.schemas import DrainReport
from discovery_ingest.worker.drain import run_worker_drain
from discovery_ingest.worker.policy import DrainPolicy
from discovery_ingest.worker.run import run_recorded_drain

from eval_fakes import long_page_html
from extract_fakes import PAGE_URL
from llm_worker_fakes import MODEL, PAGE_HTML, SERVICE, LlmApi, ScriptedLlm, llm_task, resources
from render_fakes import robots_fetcher

POLICY = DrainPolicy(max_tasks=5, kinds=("llm_extract",), neuron_budget=800)
PAGE_CHARS = len(clean_page(PAGE_HTML, PAGE_URL).text)
ESTIMATE = estimate(MODEL, PAGE_CHARS, reserved_output_tokens(PAGE_CHARS, 4000))


def _tasks(count: int = 3) -> list[dict[str, object]]:
    return [llm_task(url=f"https://portal.example/service/{number}") for number in range(count)]


def _drain(monkeypatch: pytest.MonkeyPatch, api: LlmApi, llm: ScriptedLlm, *, recorded: bool = False) -> DrainReport:
    client: DiscoveryMachineClient = api.client(monkeypatch)
    if recorded:
        return run_recorded_drain(client, robots_fetcher(), POLICY, llm=resources(llm))
    return run_worker_drain(client, robots_fetcher(), POLICY, llm=resources(llm))


def _released(api: LlmApi) -> list[tuple[str, Any]]:
    return api.named("release")


def test_a_day_with_few_neurons_left_lets_one_call_pass_it_then_releases_the_rest_with_llm_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """llm_extract · 10 neurons left: the first call reserves what is left and completes, the other 2 tasks go back."""
    api, llm = LlmApi(_tasks()), ScriptedLlm(SERVICE)
    api.ledger_remaining = 10.0

    report = _drain(monkeypatch, api, llm)

    assert (report.stop_reason, report.completed, report.released, report.succeeded) == ("llm_budget", 1, 2, True)
    assert report.llm_calls == 1 and api.ledger_remaining == pytest.approx(10.0 - cost(MODEL, 1000, 200))
    assert api.named("fail") == [] and "llm_budget" in str(_released(api)[0][1])


def test_a_denied_reservation_releases_this_task_and_the_unstarted_ones_and_stops_with_llm_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """llm_extract · the ledger is exhausted after the first call: the next reservation is denied, 2 tasks go back."""
    api = LlmApi(_tasks())
    llm = ScriptedLlm(SERVICE, on_call=lambda _call: setattr(api, "ledger_exhausted", True))

    report = _drain(monkeypatch, api, llm)

    assert (report.stop_reason, report.completed, report.released, report.succeeded) == ("llm_budget", 1, 2, True)
    assert (report.failed, report.llm_calls) == (0, 1)
    assert llm.calls == 1 and api.named("fail") == [] and "llm_budget" in str(_released(api)[0][1])


def test_a_run_budget_that_one_call_spends_stops_with_llm_budget_after_that_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """llm_extract · the first page completes and spends the budget (it may pass it); the second is released with the rest."""
    api, llm = LlmApi(_tasks()), ScriptedLlm(SERVICE)
    policy = DrainPolicy(max_tasks=5, kinds=("llm_extract",), neuron_budget=cost(MODEL, 1000, 200) - 1)

    report = run_worker_drain(api.client(monkeypatch), robots_fetcher(), policy, llm=resources(llm))

    assert (report.completed, report.released, report.stop_reason) == (1, 2, "llm_budget")
    assert report.neurons_used == pytest.approx(cost(MODEL, 1000, 200), abs=0.1)


def test_a_day_with_no_neurons_left_stops_with_llm_budget_before_claiming(monkeypatch: pytest.MonkeyPatch) -> None:
    """llm_extract · an exhausted ledger at the start: nothing is claimed, nothing released, the run succeeds."""
    api, llm = LlmApi(_tasks()), ScriptedLlm(SERVICE)
    api.ledger_exhausted = True

    report = _drain(monkeypatch, api, llm)

    assert (report.stop_reason, report.claimed, report.released, report.succeeded) == ("llm_budget", 0, 0, True)
    assert api.batches and llm.calls == 0


def test_a_quota_error_exhausts_the_day_releases_stops_with_llm_quota_and_the_run_still_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """llm_extract · Workers AI says the day is spent: ledger exhausted, reservation refunded, 3 tasks released."""
    api, llm = LlmApi(_tasks()), ScriptedLlm(LlmQuotaExceeded("daily free allocation used up"))

    report = _drain(monkeypatch, api, llm, recorded=True)

    assert (report.stop_reason, report.released, report.succeeded, report.llm_calls) == ("llm_quota", 3, True, 1)
    assert api.ledger_exhausted and api.ledger_remaining == 9000.0 and report.neurons_used == 0.0
    assert api.finishes[0]["status"] == "succeeded" and api.finishes[0]["stop_reason"] == "llm_quota"


def test_a_507_database_soft_limit_releases_and_stops_with_db_limit_after_settling_the_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """llm_extract · the mentions route refuses: the paid call is settled, then 3 tasks are released, stop db_limit."""
    api, llm = LlmApi(_tasks()), ScriptedLlm(SERVICE)
    api.mention_status, api.mention_detail = 507, '{"detail":"database_soft_limit"}'

    report = _drain(monkeypatch, api, llm)

    assert (report.stop_reason, report.released, report.succeeded, report.failed) == ("db_limit", 3, True, 0)
    assert api.ledger_remaining == pytest.approx(9000 - cost(MODEL, 1000, 200))
    assert api.posts == ["mentions"]


def test_a_503_on_the_content_route_releases_as_a_storage_problem(monkeypatch: pytest.MonkeyPatch) -> None:
    """llm_extract · the content route answering 503 (object store unavailable) is a storage stop, not a failed page."""
    api, llm = LlmApi(_tasks()), ScriptedLlm(SERVICE)
    api.content_status = 503

    report = _drain(monkeypatch, api, llm)

    assert (report.stop_reason, report.released, report.failed) == ("storage_unavailable", 3, 0)
    assert llm.calls == 0


def test_an_auth_error_releases_refunds_and_fails_the_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """llm_extract · a rejected token is infrastructure: 3 tasks released, reservation refunded, the run is failed."""
    api, llm = LlmApi(_tasks()), ScriptedLlm(LlmAuthError("Cloudflare answered 401"))

    report = _drain(monkeypatch, api, llm, recorded=True)

    assert (report.stop_reason, report.released, report.succeeded) == ("error", 3, False)
    assert api.ledger_remaining == 9000.0 and report.neurons_used == 0.0
    assert api.finishes[0]["status"] == "failed" and "Workers AI" in str(api.finishes[0]["error_detail"])


def test_a_reservation_is_settled_to_real_usage_after_a_call_and_kept_when_a_billed_call_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """llm_extract · success settles to actual - estimate; a timeout keeps the estimate and fails only that task."""
    ok = LlmApi(_tasks(1))
    assert _drain(monkeypatch, ok, ScriptedLlm(SERVICE)).neurons_used == pytest.approx(cost(MODEL, 1000, 200), abs=0.1)
    assert ok.ledger_remaining == pytest.approx(9000 - cost(MODEL, 1000, 200))

    slow = LlmApi(_tasks(2))
    report = _drain(monkeypatch, slow, ScriptedLlm(LlmRequestError("timeout", retryable=True)))

    assert (report.failed, report.released, report.stop_reason) == (2, 0, "batch_limit")
    assert slow.named("fail")[0][1]["retryable"] is True
    assert slow.ledger_remaining == pytest.approx(9000 - 2 * ESTIMATE) and report.neurons_used == 2 * ESTIMATE


def test_an_unexpected_error_after_the_call_started_leaves_the_reservation_in_place(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """llm_extract · a bug in the client may have billed the call: the error propagates and nothing is refunded."""
    api = LlmApi(_tasks(1))

    with pytest.raises(RuntimeError, match="boom"):
        _drain(monkeypatch, api, ScriptedLlm(RuntimeError("boom")))

    assert api.ledger_remaining == pytest.approx(9000 - ESTIMATE)


def test_an_unreachable_ledger_falls_back_to_the_run_budget_and_the_report_says_ledger_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """llm_extract · no ledger at the start: the run budget alone lets both pages through, the flag is reported."""
    api, llm = LlmApi(_tasks(2)), ScriptedLlm(SERVICE)
    api.ledger_remaining = None

    report = _drain(monkeypatch, api, llm)

    assert (report.completed, report.ledger_unavailable, report.stop_reason) == (2, True, "batch_limit")
    assert report.neurons_used == pytest.approx(2 * cost(MODEL, 1000, 200), abs=0.1)
    assert api.named("reserve") == []


def test_a_ledger_that_goes_away_mid_run_falls_back_to_the_run_budget_too(monkeypatch: pytest.MonkeyPatch) -> None:
    """llm_extract · the ledger answers for the first page and then stops: the second page still completes."""
    api = LlmApi(_tasks(2))

    def lose_ledger(call: int) -> None:
        api.ledger_remaining = None

    report = _drain(monkeypatch, api, ScriptedLlm(SERVICE, on_call=lose_ledger))

    assert (report.completed, report.released, report.ledger_unavailable) == (2, 0, True)


def test_the_drain_requires_llm_resources_for_the_llm_kind(monkeypatch: pytest.MonkeyPatch) -> None:
    """run_worker_drain · llm_extract without resources is a programming error, raised before anything is claimed."""
    api = LlmApi(_tasks())

    with pytest.raises(ValueError, match="LLM resources"):
        run_worker_drain(api.client(monkeypatch), robots_fetcher(), POLICY)

    assert api.batches


def test_a_drain_with_a_2500_neuron_budget_completes_three_long_pages_before_it_stops_with_llm_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """llm_extract · 25,000-character pages at 8,700 tokens in and 2,500 out cost about 745 each; reserving the page's own size lets three through."""
    api = LlmApi(_tasks(5), html=long_page_html(25_000))
    llm = ScriptedLlm(SERVICE, usage=(8_700, 2_500))
    policy = DrainPolicy(max_tasks=5, kinds=("llm_extract",), neuron_budget=2500)

    report = run_worker_drain(
        api.client(monkeypatch), robots_fetcher(), policy, llm=replace(resources(llm), max_tokens=4000)
    )

    assert report.completed >= 3 and report.stop_reason == "llm_budget"
    assert report.released == 5 - report.completed
