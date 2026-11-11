"""translate drain on the claude-code engine: claims, quota and failures through a fake CLI, calls per batch, concurrency (search-first C19)."""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator

import pytest
from discovery_ingest.operations.translate_drain import TranslateOptions, run_translate
from discovery_ingest.schemas import DrainReport
from discovery_ingest.translation.adapters.claude_code_cli import CliRequest, CliResult, CliTimeout
from discovery_ingest.translation.settings import TranslationSettings

from claude_code_fakes import MODEL, FakeCli, answered, envelope, units_in
from translate_fakes import TranslateApi, task, task_id

MODULE = "discovery_ingest.translation.adapters.claude_code"


@pytest.fixture(autouse=True)
def _claude_on_path(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(f"{MODULE}.shutil.which", lambda _name: "/usr/local/bin/claude")
    monkeypatch.setenv("CLAUDE_TRANSLATE_MODEL", MODEL)
    yield


def _install(monkeypatch: pytest.MonkeyPatch, cli: FakeCli) -> FakeCli:
    monkeypatch.setattr(f"{MODULE}.run_subprocess", cli)
    return cli


def _run(api: TranslateApi, **bounds: int) -> DrainReport:
    settings = TranslationSettings.model_validate({"TRANSLATION_ENGINE": "claude-code"})
    return run_translate(TranslateOptions(**bounds), settings, api.client())


def _prompted_locales(cli: FakeCli) -> set[str]:
    return {language for request in cli.requests for language in ("Turkish", "Ukrainian") if language in request.stdin}


def test_a_claude_code_drain_translates_tr_and_uk_with_zero_neurons_and_no_ledger_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """translate drain · tr and uk units are translated through the CLI; no neuron is spent and the ledger is never written."""
    api = TranslateApi([task(0, "tr"), task(1, "uk"), task(2, "tr"), task(3, "uk")])
    cli = _install(monkeypatch, FakeCli(answered))

    report = _run(api, max_batches=1)

    assert (report.completed, report.failed, report.stop_reason) == (4, 0, "batch_limit")
    assert _prompted_locales(cli) == {"Turkish", "Ukrainian"}
    assert (report.neurons_used, report.ledger_unavailable) == (0.0, False)
    assert api.ledger.calls == []
    assert report.tokens_used > 0 and report.auth_mode == "claude-login" and report.llm_calls == 2
    assert {(item["engine"], item["model"]) for item in api.posted()} == {("claude-code", MODEL)}


def test_a_rate_limit_stops_the_drain_and_releases_the_batch_without_consuming_an_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """translate drain · a usage limit from the CLI is a quota stop: the batch is released (no attempt used), nothing is failed."""
    api = TranslateApi([task(number, "tr") for number in range(3)])
    _install(
        monkeypatch,
        FakeCli(lambda _r: CliResult(1, envelope(is_error=True, result="API Error: Rate limit reached"), "")),
    )

    report = _run(api, max_batches=1)

    assert (report.stop_reason, report.succeeded, report.released, report.completed) == ("llm_quota", True, 3, 0)
    assert api.bodies["release"][0]["task_ids"] == [task_id(number) for number in range(3)]
    assert not api.bodies["fail"]


def test_a_timeout_fails_the_batch_retryably_and_the_drain_goes_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """translate drain · a call that times out fails its tasks as retryable; the drain counts them and goes on."""
    api = TranslateApi([task(number, "tr") for number in range(2)])

    def reply(_request: CliRequest) -> CliResult:
        raise CliTimeout("no answer within 240 seconds")

    _install(monkeypatch, FakeCli(reply))

    report = _run(api, max_batches=1)

    assert {body["retryable"] for body in api.bodies["fail"]} == {True}
    assert (report.failed, report.succeeded) == (2, True)


def test_not_logged_in_stops_the_drain_as_an_infrastructure_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """translate drain · 'not logged in' stops the drain as an error, releases the batch and fails nothing."""
    api = TranslateApi([task(number, "tr") for number in range(2)])
    _install(
        monkeypatch,
        FakeCli(lambda _r: CliResult(1, envelope(is_error=True, result="Not logged in · Please run /login"), "")),
    )

    report = _run(api, max_batches=1)

    assert (report.stop_reason, report.succeeded, report.released) == ("error", False, 2)
    assert report.error is not None and "credentials" in report.error and not api.bodies["fail"]


def test_an_unreadable_answer_twice_stores_nothing_and_fails_the_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    """translate drain · invalid JSON is repeated once; a second unreadable answer fails the batch and nothing is stored."""
    api = TranslateApi([task(number, "tr") for number in range(2)])
    cli = _install(monkeypatch, FakeCli(lambda _r: CliResult(0, "not json at all", "")))

    report = _run(api, max_batches=1)

    assert len(cli.requests) == 2 and not api.bodies["complete"]
    assert (report.completed, report.failed) == (0, 2)


def test_a_usage_limit_during_the_repair_still_posts_the_units_that_were_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    """translate drain · the repair call hits the usage limit: the unit that was valid is posted; the other is released."""
    api = TranslateApi([task(0, "tr"), task(1, "tr")])
    calls: list[CliRequest] = []

    def reply(request: CliRequest) -> CliResult:
        calls.append(request)
        if len(calls) > 1:
            return CliResult(1, envelope(is_error=True, result="API Error: Rate limit reached"), "")
        valid, lossy = units_in(request)
        answer = {
            "units": [
                {"key": valid["key"], "title": f"[en] {valid['title']}", "description": f"[en] {valid['description']}"},
                {
                    "key": lossy["key"],
                    "title": "[en] Reisepass beantragen",
                    "description": f"[en] {lossy['description']}",
                },
            ]
        }
        return CliResult(0, envelope(answer), "")

    _install(monkeypatch, FakeCli(reply))

    report = _run(api, max_batches=1)

    assert [item["task_id"] for item in api.posted()] == [task_id(0)]
    assert api.bodies["release"][0]["task_ids"] == [task_id(1)] and not api.bodies["fail"]
    assert (report.stop_reason, report.completed, report.released) == ("llm_quota", 1, 1)


def test_a_failing_validator_is_repaired_once_through_the_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    """translate drain · a translation that loses its numbers is repaired by one more call; the repaired text is stored."""
    api = TranslateApi([task(0, "tr")])
    calls: list[CliRequest] = []

    def reply(request: CliRequest) -> CliResult:
        calls.append(request)
        if len(calls) > 1:
            return answered(request)
        lossy = [
            {"key": u["key"], "title": "[en] Reisepass", "description": "[en] Der Reisepass"} for u in units_in(request)
        ]
        return CliResult(0, envelope({"units": lossy}), "")

    _install(monkeypatch, FakeCli(reply))

    report = _run(api, max_batches=1)

    assert (report.completed, report.repaired, report.llm_calls) == (1, 1, 2)


def test_a_batch_is_cut_into_calls_of_at_most_twenty_units_run_two_at_a_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """translate drain · 25 units of one locale make a call of 20 and a call of 5; with concurrency 2 both are in flight at once."""
    api = TranslateApi([task(number, "tr") for number in range(25)])
    both_started = threading.Barrier(2, timeout=10)
    sizes: list[int] = []

    def reply(request: CliRequest) -> CliResult:
        sizes.append(len(units_in(request)))
        both_started.wait()
        return answered(request)

    _install(monkeypatch, FakeCli(reply))

    report = _run(api, max_tasks=25, max_batches=1, concurrency=2)

    assert sorted(sizes) == [5, 20]
    assert (report.completed, report.llm_calls, report.succeeded) == (25, 2, True)


def test_concurrency_of_one_runs_the_calls_one_at_a_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """translate drain · with concurrency 1 no two CLI calls overlap."""
    api = TranslateApi([task(number, "tr") for number in range(25)])
    state = {"running": 0, "peak": 0}

    def reply(request: CliRequest) -> CliResult:
        state["running"] += 1
        state["peak"] = max(state["peak"], state["running"])
        time.sleep(0.01)
        state["running"] -= 1
        return answered(request)

    _install(monkeypatch, FakeCli(reply))

    report = _run(api, max_tasks=25, max_batches=1, concurrency=1)

    assert (state["peak"], report.completed) == (1, 25)


def test_the_concurrency_option_is_bounded_between_one_and_four() -> None:
    """translate drain · the bound is checked before anything is claimed: 0 and 5 are refused."""
    for value in (0, 5):
        with pytest.raises(ValueError, match="concurrency must be between 1 and 4"):
            TranslateOptions(concurrency=value).policy()
