"""embed drain: claim, embed, complete; every limit and error maps to a stop reason or a per-task outcome (search-first C6)."""

from __future__ import annotations

import pytest
from discovery_ingest.extract.embedding.client import Embedder
from discovery_ingest.extract.llm.errors import LlmAuthError, LlmQuotaExceeded, LlmRequestError
from discovery_ingest.schemas import DrainReport
from discovery_ingest.worker.embed_drain import EmbedDeps, run_embed_drain
from discovery_ingest.worker.policy import DrainPolicy

from embed_fakes import API_KEY, MODEL, EmbedApi, ScriptedEmbedder, task, task_id, vector_of
from embedding_transport import TOKEN, embedding_client, embedding_success, failure, vectors
from ledger_fakes import FakeLedger
from llm_transport import ACCOUNT_ID


def _drain(
    api: EmbedApi,
    embedder: Embedder,
    *,
    max_tasks: int = 50,
    max_batches: int = 10,
    neuron_budget: float = 1000.0,
) -> DrainReport:
    policy = DrainPolicy(max_tasks=max_tasks, max_batches=max_batches, neuron_budget=neuron_budget)
    return run_embed_drain(EmbedDeps(client=api.client(), embedder=embedder, model=MODEL), policy)


def _ids(*numbers: int) -> list[str]:
    return [task_id(number) for number in numbers]


def test_claims_embeds_in_batches_and_completes_in_order() -> None:
    """embed drain · claims, embeds in batches and completes: batch sizes, vector order and the report counts."""
    api = EmbedApi([task(number) for number in range(5)])
    embedder = ScriptedEmbedder()

    report = _drain(api, embedder, max_tasks=2, max_batches=3)

    assert [len(batch) for batch in embedder.batches] == [2, 2, 1]
    posted = [item for body in api.bodies["complete"] for item in body["items"]]
    assert [item["task_id"] for item in posted] == _ids(0, 1, 2, 3, 4)
    assert [tuple(item["vector"]) for item in posted] == [vector_of(f"text-{number}") for number in range(5)]
    assert {item["model"] for item in posted} == {MODEL} and posted[0]["text_hash"] == "hash-0"
    assert (report.batches, report.claimed, report.completed, report.failed) == (3, 5, 5, 0)
    assert (report.stop_reason, report.succeeded, report.llm_calls, report.remaining) == ("batch_limit", True, 3, 0)
    assert report.neurons_used == pytest.approx(0.3)


def test_stops_with_queue_empty_after_the_last_claim_returns_nothing() -> None:
    """embed drain · stops with queue_empty."""
    api = EmbedApi([task(number) for number in range(3)])

    report = _drain(api, ScriptedEmbedder(), max_tasks=2)

    assert (report.stop_reason, report.batches, report.claimed, report.completed) == ("queue_empty", 3, 3, 3)


def test_an_empty_queue_makes_no_embedding_call_and_reserves_nothing() -> None:
    """embed drain · an empty queue stops queue_empty without a provider call or a reservation."""
    api = EmbedApi([])
    embedder = ScriptedEmbedder()

    report = _drain(api, embedder)

    assert (report.stop_reason, report.claimed, report.neurons_used) == ("queue_empty", 0, 0.0)
    assert embedder.batches == [] and "reserve" not in api.ledger.actions()


def test_stale_and_stored_results_are_both_counted_and_nothing_is_retried() -> None:
    """embed drain · stale and stored results are both counted; a stale task is not failed, released or re-embedded."""
    api = EmbedApi([task(number) for number in range(3)])
    api.outcomes[task_id(1)] = ("stale", None)
    embedder = ScriptedEmbedder()

    report = _drain(api, embedder, max_batches=1)

    assert (report.completed, report.stale, report.failed, report.released) == (3, 1, 0, 0)
    assert len(embedder.batches) == 1 and not api.bodies["fail"] and not api.bodies["release"]


def test_a_rejected_item_is_logged_and_counted_failed_without_stopping(capsys: pytest.CaptureFixture[str]) -> None:
    """embed drain · a rejected result (a replayed complete) is logged with its reason and is not fatal."""
    api = EmbedApi([task(number) for number in range(3)])
    api.outcomes[task_id(0)] = ("rejected", "task is not claimed by this key")

    report = _drain(api, ScriptedEmbedder(), max_batches=1)

    assert (report.completed, report.failed, report.succeeded) == (2, 1, True)
    assert "task is not claimed by this key" in capsys.readouterr().err


def test_quota_exhaustion_stops_with_llm_quota_and_releases_the_whole_batch() -> None:
    """embed drain · quota exhaustion stops with llm_quota, releases the batch and consumes no attempt."""
    api = EmbedApi([task(number) for number in range(3)])

    report = _drain(api, ScriptedEmbedder(LlmQuotaExceeded("daily free allocation used up")))

    assert (report.stop_reason, report.succeeded, report.claimed, report.released) == ("llm_quota", True, 3, 3)
    assert api.bodies["release"][0]["task_ids"] == _ids(0, 1, 2) and "llm_quota" in api.bodies["release"][0]["reason"]
    assert not api.bodies["fail"] and not api.bodies["complete"]
    assert "exhaust" in api.ledger.actions() and api.ledger.remaining == 9000.0


def test_an_exhausted_ledger_stops_with_llm_budget_before_claiming_anything() -> None:
    """embed drain · an exhausted ledger stops with llm_budget before any claim or call."""
    api = EmbedApi([task(0)], ledger=FakeLedger(0.0, exhausted=True))
    embedder = ScriptedEmbedder()

    report = _drain(api, embedder)

    assert (report.stop_reason, report.claimed, report.succeeded) == ("llm_budget", 0, True)
    assert not api.bodies["claim"] and embedder.batches == []


def test_a_reached_run_budget_stops_with_llm_budget_and_releases_the_unstarted_batch() -> None:
    """embed drain · an exhausted reservation stops with llm_budget before the call and releases that batch."""
    api = EmbedApi([task(number) for number in range(4)])
    embedder = ScriptedEmbedder(neurons=5.0)

    report = _drain(api, embedder, max_tasks=2, neuron_budget=1.0)

    assert (report.stop_reason, report.completed, report.released) == ("llm_budget", 2, 2)
    assert len(embedder.batches) == 1 and api.bodies["release"][0]["task_ids"] == _ids(2, 3)
    assert not api.bodies["fail"]


@pytest.mark.parametrize("retryable", [True, False])
def test_a_request_error_fails_the_batch_tasks_and_the_drain_goes_on(retryable: bool) -> None:
    """embed drain · a 5xx fails the batch retryably (a plain rejection permanently) and the next batch still runs."""
    api = EmbedApi([task(number) for number in range(4)])
    embedder = ScriptedEmbedder(LlmRequestError("provider answered 503", retryable=retryable), None)

    report = _drain(api, embedder, max_tasks=2)

    fails = api.bodies["fail"]
    assert [body["task_id"] for body in fails] == _ids(0, 1) and {body["retryable"] for body in fails} == {retryable}
    assert (report.failed, report.completed, report.succeeded, report.stop_reason) == (2, 2, True, "queue_empty")
    assert api.ledger.remaining == pytest.approx(9000.0 - 0.1)


def test_a_rejected_token_stops_as_infrastructure_and_releases_the_batch() -> None:
    """embed drain · a 401 stops with error (succeeded false), releases the batch and fails nothing."""
    api = EmbedApi([task(number) for number in range(2)])

    report = _drain(api, ScriptedEmbedder(LlmAuthError("Authentication error")))

    assert (report.stop_reason, report.succeeded, report.released) == ("error", False, 2)
    assert report.error is not None and "credentials" in report.error and not api.bodies["fail"]


def test_the_database_soft_limit_on_complete_stops_with_db_limit_and_releases_the_batch() -> None:
    """embed drain · the 507 soft limit on complete stops with db_limit and releases the batch."""
    api = EmbedApi([task(number) for number in range(2)])
    api.forced["complete"] = (507, "database_soft_limit")

    report = _drain(api, ScriptedEmbedder())

    assert (report.stop_reason, report.succeeded, report.released, report.completed) == ("db_limit", True, 2, 0)
    assert not api.bodies["fail"]


def test_the_database_soft_limit_on_claim_stops_with_db_limit() -> None:
    """embed drain · the 507 soft limit on claim stops with db_limit having claimed nothing."""
    api = EmbedApi([task(0)])
    api.forced["claim"] = (507, "database_soft_limit")

    report = _drain(api, ScriptedEmbedder())

    assert (report.stop_reason, report.claimed, report.succeeded) == ("db_limit", 0, True)


def test_a_server_error_on_complete_stops_as_error_and_releases_the_batch() -> None:
    """embed drain · a 500 on complete is infrastructure: stop error, release, never fail the tasks."""
    api = EmbedApi([task(number) for number in range(2)])
    api.forced["complete"] = (500, "boom")

    report = _drain(api, ScriptedEmbedder())

    assert (report.stop_reason, report.succeeded, report.released) == ("error", False, 2)
    assert not api.bodies["fail"]


def test_a_conflict_on_fail_and_on_release_is_not_fatal() -> None:
    """embed drain · fail and release answer 409 for a task this key does not hold: counted skipped, never raised."""
    api = EmbedApi([task(number) for number in range(2)])
    api.forced["fail"] = (409, "task is not claimed by this key")

    report = _drain(api, ScriptedEmbedder(LlmRequestError("503", retryable=True)), max_batches=1)

    assert (report.failed, report.skipped, report.succeeded) == (0, 2, True)

    api = EmbedApi([task(number) for number in range(2)])
    api.forced["release"] = (409, "task is not claimed by this key")

    report = _drain(api, ScriptedEmbedder(LlmQuotaExceeded("used up")))

    assert (report.stop_reason, report.released, report.succeeded) == ("llm_quota", 0, True)


def test_a_short_response_fails_the_whole_batch_and_posts_no_vector() -> None:
    """embed client · fewer vectors than texts fails the batch retryably; no item is silently dropped or stored."""
    api = EmbedApi([task(number) for number in range(3)])
    embedder = embedding_client(lambda _request: embedding_success(vectors(2, 4)))

    report = _drain(api, embedder, max_batches=1)

    assert [body["task_id"] for body in api.bodies["fail"]] == _ids(0, 1, 2)
    assert {body["retryable"] for body in api.bodies["fail"]} == {True}
    assert not api.bodies["complete"] and (report.failed, report.completed) == (3, 0)


def test_secrets_never_reach_the_report() -> None:
    """embed drain · neither the Workers AI token, the account id nor the API key appears in a report or a failure."""
    api = EmbedApi([task(0)])
    denied = embedding_client(lambda _request: failure(401, 10000, f"Authentication error {TOKEN} {ACCOUNT_ID}"))

    auth_report = _drain(api, denied)

    api = EmbedApi([task(0)])
    api.forced["complete"] = (500, f"upstream echoed {API_KEY}")
    api_report = _drain(api, ScriptedEmbedder())

    for report in (auth_report, api_report):
        text = report.model_dump_json()
        assert TOKEN not in text and ACCOUNT_ID not in text and API_KEY not in text
    assert auth_report.error is not None and api_report.error is not None


def test_a_drain_policy_without_a_neuron_budget_is_refused() -> None:
    """embed drain · a drain without a neuron budget raises before anything is claimed."""
    api = EmbedApi([task(0)])

    with pytest.raises(ValueError, match="neuron_budget"):
        run_embed_drain(
            EmbedDeps(client=api.client(), embedder=ScriptedEmbedder(), model=MODEL),
            DrainPolicy(max_tasks=1),
        )

    assert not api.bodies["claim"]


def test_a_server_error_on_claim_stops_as_error_with_a_report() -> None:
    """embed drain · a 500 on claim is infrastructure: a report with stop error and succeeded false, never a traceback."""
    api = EmbedApi([task(0)])
    api.forced["claim"] = (500, f"boom {API_KEY}")

    report = _drain(api, ScriptedEmbedder())

    assert (report.stop_reason, report.succeeded, report.claimed) == ("error", False, 0)
    assert report.error is not None and "500" in report.error and API_KEY not in report.error


def test_an_unavailable_queue_summary_is_reported_as_unknown_not_as_a_failure() -> None:
    """embed drain · a summary that cannot be read leaves remaining unknown; the drain still succeeded."""
    api = EmbedApi([])
    api.forced["summary"] = (500, "boom")

    report = _drain(api, ScriptedEmbedder())

    assert (report.remaining, report.remaining_unknown, report.succeeded) == (None, True, True)


def test_a_timeout_on_complete_stops_as_error_and_releases_the_batch() -> None:
    """embed drain · a transport failure on complete (outcome unknown) stops error and hands the batch back."""
    api = EmbedApi([task(number) for number in range(2)])
    api.unreachable.add("complete")

    report = _drain(api, ScriptedEmbedder())

    assert (report.stop_reason, report.succeeded, report.released) == ("error", False, 2)
    assert report.error is not None and "ReadTimeout" in report.error and not api.bodies["fail"]


def test_a_timeout_on_claim_stops_as_error_with_a_report() -> None:
    """embed drain · a transport failure on claim is a report with stop error, not a traceback."""
    api = EmbedApi([task(0)])
    api.unreachable.add("claim")

    report = _drain(api, ScriptedEmbedder())

    assert (report.stop_reason, report.succeeded, report.claimed) == ("error", False, 0)


def test_a_timeout_on_fail_stops_as_error_and_releases_the_batch() -> None:
    """embed drain · when failing a refused batch cannot reach the API, the batch is released, not lost."""
    api = EmbedApi([task(number) for number in range(2)])
    api.unreachable.add("fail")

    report = _drain(api, ScriptedEmbedder(LlmRequestError("503", retryable=True)))

    assert (report.stop_reason, report.succeeded, report.released) == ("error", False, 2)
