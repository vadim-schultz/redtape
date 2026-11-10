"""``embed drain`` and ``embed summary``: bounds, credentials, the JSON report and the skip exit of the workflow (search-first C6)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from discovery_ingest.cli import main

from embed_fakes import EmbedApi, task
from embedding_transport import TOKEN, embedding_success, failure, vectors
from llm_transport import ACCOUNT_ID

EXIT_SKIP = 3


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DISCOVERY_API_URL", "https://redtape.test")
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", ACCOUNT_ID)
    monkeypatch.setenv("CLOUDFLARE_AI_API_TOKEN", TOKEN)
    monkeypatch.setattr("discovery_ingest.operations.embed_drain.EMBED_MIN_INTERVAL_SECONDS", 0.0)


def _install(
    monkeypatch: pytest.MonkeyPatch, api: EmbedApi, answer: httpx.Response | None = None
) -> list[httpx.Request]:
    """Serve the machine API from ``api`` and Workers AI from ``answer`` (one vector of width 4 per text by default)."""
    seen: list[httpx.Request] = []

    def cloudflare(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        count = len(json.loads(request.content)["text"])
        return answer or embedding_success(vectors(count, 4), {"prompt_tokens": 10, "neurons": 0.1})

    api.install(monkeypatch, cloudflare)
    return seen


def test_the_command_prints_one_json_report_and_never_a_secret(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """embed drain · prints one DrainReport as JSON, exit 0, with no token, account id or API key."""
    api = EmbedApi([task(number) for number in range(3)])
    _install(monkeypatch, api)

    code = main(["embed", "drain", "--max-batches", "5"])

    out = capsys.readouterr().out
    report = json.loads(out)
    assert code == 0 and (report["claimed"], report["completed"], report["stop_reason"]) == (3, 3, "queue_empty")
    assert api.bodies["claim"][0]["model"] == "@cf/qwen/qwen3-embedding-0.6b"
    assert TOKEN not in out and ACCOUNT_ID not in out and "test-machine-key" not in out


def test_the_budget_flags_reach_the_policy(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """embed drain · --max-tasks bounds the claim size and --neuron-budget the run's spend."""
    api = EmbedApi([task(number) for number in range(4)])
    _install(monkeypatch, api)

    argv = ["--max-tasks", "2", "--max-batches", "5", "--neuron-budget", "500", "--time-budget-seconds", "60"]

    code = main(["embed", "drain", *argv])

    assert code == 0 and {body["limit"] for body in api.bodies["claim"]} == {2}
    assert json.loads(capsys.readouterr().out)["claimed"] == 4


@pytest.mark.parametrize("argv", [["--max-tasks", "0"], ["--max-tasks", "51"], ["--neuron-budget", "0"]])
def test_invalid_bounds_exit_2_before_any_request(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], argv: list[str]
) -> None:
    """embed drain · an out-of-range bound exits 2 and claims nothing."""
    api = EmbedApi([task(0)])
    api.install(monkeypatch)

    assert main(["embed", "drain", *argv]) == 2
    assert not api.bodies["claim"] and "invalid drain bounds" in capsys.readouterr().err


def test_missing_credentials_exit_2_naming_only_the_variable(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """embed drain · a missing Workers AI variable exits 2 before any request."""
    monkeypatch.delenv("CLOUDFLARE_AI_API_TOKEN")
    api = EmbedApi([task(0)])
    api.install(monkeypatch)

    assert main(["embed", "drain"]) == 2
    assert "CLOUDFLARE_AI_API_TOKEN" in capsys.readouterr().err and not api.bodies["claim"]


def test_an_unreadable_ledger_refuses_to_start(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """embed drain · without a readable neuron ledger the drain does not spend: exit 1 and nothing claimed."""
    api = EmbedApi([task(0)])
    api.ledger.down = True
    api.install(monkeypatch)

    assert main(["embed", "drain"]) == 1
    assert "ledger" in capsys.readouterr().err and not api.bodies["claim"]


def test_a_rejected_token_exits_1_with_the_report(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """embed drain · a 401 from Workers AI prints the report with succeeded false and exits 1, scrubbed."""
    api = EmbedApi([task(0)])
    _install(monkeypatch, api, failure(401, 10000, f"Authentication error {TOKEN}"))

    code = main(["embed", "drain"])

    out = capsys.readouterr().out
    assert code == 1 and json.loads(out)["succeeded"] is False and TOKEN not in out


def test_summary_prints_the_counts_and_exits_0(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """embed summary · prints the queue counts as one JSON object."""
    api = EmbedApi([task(0), task(1)])
    api.install(monkeypatch)

    code = main(["embed", "summary"])

    assert code == 0 and json.loads(capsys.readouterr().out)["pending_ready"] == 2


def test_require_pending_skips_with_exit_3_when_nothing_is_ready(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """workflow · the precheck helper exits 3 when pending_ready is 0, and 0 when something is ready."""
    api = EmbedApi([])
    api.install(monkeypatch)

    assert main(["embed", "summary", "--require-pending"]) == EXIT_SKIP
    assert "nothing to embed" in capsys.readouterr().err

    api.queue.append(task(0))
    assert main(["embed", "summary", "--require-pending"]) == 0
