"""``translate drain`` and ``translate summary``: bounds, engine setup, the JSON report and the skip exit of the workflow (search-first C15)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from discovery_ingest.cli import main

from llm_transport import ACCOUNT_ID, TOKEN, failure, success
from translate_fakes import TranslateApi, task

EXIT_SKIP = 3


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DISCOVERY_API_URL", "https://redtape.test")
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", ACCOUNT_ID)
    monkeypatch.setenv("CLOUDFLARE_AI_API_TOKEN", TOKEN)
    monkeypatch.setenv("TRANSLATION_ENGINE", "llm")
    monkeypatch.setenv("LLM_MODEL", "@cf/qwen/qwen3-30b-a3b-fp8")
    monkeypatch.setattr("discovery_ingest.operations.translate_drain.TRANSLATE_MIN_INTERVAL_SECONDS", 0.0)
    yield


def _answer(request: httpx.Request) -> httpx.Response:
    units = json.loads(json.loads(request.content)["messages"][-1]["content"])["units"]
    body = {
        "units": [
            {"key": u["key"], "title": f"[xx] {u['title']}", "description": f"[xx] {u['description']}"} for u in units
        ]
    }
    return success(body, {"prompt_tokens": 100, "completion_tokens": 60, "neurons": 3.0})


def _install(monkeypatch: pytest.MonkeyPatch, api: TranslateApi, cloudflare: object = _answer) -> list[httpx.Request]:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return cloudflare(request)  # type: ignore[operator]

    api.install(monkeypatch, handler)
    return seen


def test_the_command_prints_one_json_report_and_never_a_secret(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """translate drain · prints one DrainReport as JSON, exit 0, translates through Workers AI, no secret printed."""
    api = TranslateApi([task(number, "tr") for number in range(3)])
    seen = _install(monkeypatch, api)

    code = main(["translate", "drain", "--max-batches", "5"])

    out = capsys.readouterr().out
    report = json.loads(out)
    assert code == 0 and (report["claimed"], report["completed"], report["stop_reason"]) == (3, 3, "queue_empty")
    assert (
        len(seen) == 1
        and api.posted()[0]["engine"] == "llm"
        and api.posted()[0]["model"] == "@cf/qwen/qwen3-30b-a3b-fp8"
    )
    assert TOKEN not in out and ACCOUNT_ID not in out and "test-machine-key" not in out


def test_the_flags_reach_the_policy_and_the_floor_default_protects_the_day(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """translate drain · --max-tasks bounds the claim; QUERY_EMBED_RESERVE leaves the floor: stops llm_budget below it."""
    api = TranslateApi([task(number) for number in range(4)])
    _install(monkeypatch, api)
    argv = ["--max-tasks", "2", "--max-batches", "5", "--neuron-budget", "500", "--time-budget-seconds", "60"]

    assert main(["translate", "drain", *argv]) == 0 and {body["limit"] for body in api.bodies["claim"]} == {2}
    capsys.readouterr()

    monkeypatch.setenv("QUERY_EMBED_RESERVE", "8999")
    api.queue = [task(number) for number in range(4)]
    api.ledger.remaining = 9000.0
    main(["translate", "drain", *argv])
    assert json.loads(capsys.readouterr().out)["stop_reason"] == "llm_budget" and api.ledger.remaining >= 8999.0


@pytest.mark.parametrize("argv", [["--max-tasks", "0"], ["--max-tasks", "51"], ["--neuron-budget", "0"]])
def test_invalid_bounds_exit_2_before_any_request(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], argv: list[str]
) -> None:
    """translate drain · an out-of-range bound exits 2 and claims nothing."""
    api = TranslateApi([task(0)])
    api.install(monkeypatch)

    assert main(["translate", "drain", *argv]) == 2
    assert not api.bodies["claim"] and "invalid drain bounds" in capsys.readouterr().err


def test_an_unknown_engine_exits_2_naming_the_registered_ones(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """translate drain · TRANSLATION_ENGINE that is not registered exits 2 before any request."""
    monkeypatch.setenv("TRANSLATION_ENGINE", "nope")
    api = TranslateApi([task(0)])
    api.install(monkeypatch)

    assert main(["translate", "drain"]) == 2
    assert "registered" in capsys.readouterr().err and not api.bodies["claim"]


def test_missing_engine_credentials_exit_2_naming_only_the_variable(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """translate drain · an engine that cannot start (a missing variable) exits 2 and claims nothing."""
    monkeypatch.delenv("CLOUDFLARE_AI_API_TOKEN")
    api = TranslateApi([task(0)])
    api.install(monkeypatch)

    assert main(["translate", "drain"]) == 2
    err = capsys.readouterr().err
    assert "CLOUDFLARE_AI_API_TOKEN" in err and ACCOUNT_ID not in err and not api.bodies["claim"]


def test_an_unreadable_ledger_refuses_to_start(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """translate drain · without a readable neuron ledger the drain does not spend (the floor is unprovable): exit 1."""
    api = TranslateApi([task(0)])
    api.ledger.down = True
    api.install(monkeypatch)

    assert main(["translate", "drain"]) == 1
    assert "ledger" in capsys.readouterr().err and not api.bodies["claim"]


def test_a_rejected_token_exits_1_with_the_report(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """translate drain · a 401 from Workers AI prints the report with succeeded false and exits 1, scrubbed."""
    api = TranslateApi([task(0)])
    _install(monkeypatch, api, lambda _r: failure(401, 10000, f"Authentication error {TOKEN}"))

    code = main(["translate", "drain"])

    out = capsys.readouterr().out
    assert code == 1 and json.loads(out)["succeeded"] is False and TOKEN not in out


def test_summary_prints_the_counts_per_locale_and_the_total(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """translate summary · prints the queue counts as one JSON object with the total ready."""
    api = TranslateApi([task(0), task(1)])
    api.install(monkeypatch)

    code = main(["translate", "summary"])

    data = json.loads(capsys.readouterr().out)
    assert code == 0 and data["pending_ready"] == 2 and [row["locale"] for row in data["locales"]] == ["en", "tr"]


def test_require_pending_skips_with_exit_3_when_nothing_is_ready(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """workflow · the precheck helper exits 3 when pending_ready is 0 in every locale, and 0 when something is ready."""
    api = TranslateApi([])
    api.install(monkeypatch)

    assert main(["translate", "summary", "--require-pending"]) == EXIT_SKIP
    assert "nothing to translate" in capsys.readouterr().err

    api.queue.append(task(0))
    assert main(["translate", "summary", "--require-pending"]) == 0


@pytest.mark.parametrize(("mode", "completed"), [("strict", 0), ("advisory", 1)])
def test_the_glossary_mode_decides_whether_a_glossary_finding_fails_the_card(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], mode: str, completed: int
) -> None:
    """translate drain · TRANSLATION_GLOSSARY_MODE advisory posts a card whose only finding is glossary adherence; strict fails it."""
    monkeypatch.setenv("TRANSLATION_GLOSSARY_MODE", mode)
    api = TranslateApi([{**task(0, "tr"), "title": "Antrag stellen 0"}])
    _install(monkeypatch, api)

    assert main(["translate", "drain", "--max-batches", "1"]) in (0, 1)

    report = json.loads(capsys.readouterr().out)
    assert report["completed"] == completed
    if mode == "advisory":
        assert api.posted()[0]["title"] == "[xx] Antrag stellen 0"


def test_the_probe_needs_a_locale_for_every_engine_but_azure_translator(capsys: pytest.CaptureFixture[str]) -> None:
    """translate probe · without --locale the llm engine exits 2 naming the option; azure-translator probes every target locale."""
    assert main(["translate", "probe", "--engine", "llm"]) == 2
    assert "--locale" in capsys.readouterr().err


def test_the_engine_and_band_flags_name_the_engine_and_the_band_in_every_claim(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """translate drain · --engine and the priority band are sent with the claim, and the drain runs on that engine."""
    api = TranslateApi([task(number, "tr") for number in range(2)])
    _install(monkeypatch, api)

    code = main(["translate", "drain", "--engine", "llm", "--priority-min", "600", "--priority-max", "1000"])

    capsys.readouterr()
    assert code == 0
    assert api.bodies["claim"][0] == {"limit": 10, "engine": "llm", "priority_min": 600, "priority_max": 1000}
    assert api.posted()[0]["engine"] == "llm"


@pytest.mark.parametrize(
    "argv",
    [
        ["--engine", "not-an-engine"],
        ["--priority-min", "700", "--priority-max", "600"],
        ["--unit", "snapshot", "--engine", "llm"],
        ["--unit", "snapshot", "--priority-min", "600"],
    ],
)
def test_an_unknown_engine_an_inverted_band_or_a_card_flag_on_snapshots_exits_2_before_any_claim(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], argv: list[str]
) -> None:
    """translate drain · a bad engine, an inverted band, or a card-only flag on --unit snapshot exits 2 and claims nothing."""
    api = TranslateApi([task(0)])
    api.install(monkeypatch)

    assert main(["translate", "drain", *argv]) == 2
    assert not api.bodies["claim"]
    assert capsys.readouterr().err
