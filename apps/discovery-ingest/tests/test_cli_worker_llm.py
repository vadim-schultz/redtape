"""worker drain with llm_extract: the safety checks before claiming and the report fields (chapter E6, C)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from discovery_ingest.budget import BudgetGuard
from discovery_ingest.cli import _build_parser, _drain_policy, main
from discovery_ingest.extract.llm.prices import cost
from discovery_ingest.schemas import WORKER_DEFAULT_TASK_KINDS
from discovery_ingest.worker.handler_table import handler_table
from discovery_ingest.worker.llm_drain import open_llm_drain
from discovery_ingest.worker.llm_extract import LlmExtractHandler, no_after_extract
from discovery_ingest.worker.policy import DrainPolicy

from llm_transport import ACCOUNT_ID, TOKEN, failure, success
from llm_worker_fakes import MODEL, SERVICE, LlmApi, ScriptedLlm, llm_task, resources

DRAIN = ["worker", "drain", "--kinds", "llm_extract", "--neuron-budget", "800"]
USAGE = {"prompt_tokens": 1000, "completion_tokens": 200}


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DISCOVERY_API_URL", "https://redtape.test")
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", ACCOUNT_ID)
    monkeypatch.setenv("CLOUDFLARE_AI_API_TOKEN", TOKEN)
    monkeypatch.setenv("LLM_MODEL", MODEL)
    monkeypatch.setattr("time.sleep", lambda _seconds: None)


def _api(monkeypatch: pytest.MonkeyPatch, tasks: int = 1) -> LlmApi:
    api = LlmApi([llm_task(url=f"https://portal.example/service/{number}") for number in range(tasks)])
    api.client(monkeypatch)
    api.cloudflare = lambda request: success(SERVICE, USAGE)
    return api


def _nothing_was_claimed(api: LlmApi) -> bool:
    task_calls = {"complete", "fail", "release"}
    return bool(api.batches) and not task_calls & {name for name, _task, _body in api.calls}


def test_default_kinds_exclude_llm_extract_and_the_dispatch_table_contains_it(monkeypatch: pytest.MonkeyPatch) -> None:
    """kinds · a plain drain never claims llm_extract; a drain of the kind has a handler for it."""
    api = LlmApi([])
    guard = BudgetGuard(api.client(monkeypatch))
    policy = DrainPolicy(kinds=("llm_extract",), neuron_budget=800)
    drain = open_llm_drain(policy, guard, resources(ScriptedLlm(SERVICE)), no_after_extract)
    assert drain is not None

    table = handler_table((), (None, None, lambda task, artifact: None), drain)

    assert "llm_extract" not in WORKER_DEFAULT_TASK_KINDS
    assert isinstance(table["llm_extract"], LlmExtractHandler)
    assert "llm_extract" not in handler_table((), (None, None, lambda task, artifact: None), None)


def test_llm_drains_claim_small_batches_by_default_and_plain_drains_keep_fifty() -> None:
    """worker drain · --max-tasks defaults to 5 for llm_extract and 50 otherwise; an explicit value wins."""
    parser = _build_parser()

    assert _drain_policy(parser.parse_args(DRAIN)).max_tasks == 5
    assert _drain_policy(parser.parse_args(["worker", "drain"])).max_tasks == 50
    assert _drain_policy(parser.parse_args([*DRAIN, "--max-tasks", "2"])).max_tasks == 2


def test_a_drain_without_the_ai_token_or_the_model_or_a_known_price_fails_before_claiming(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """worker drain · each missing setting exits 2 naming the variable (never a value) and claims nothing."""
    api = _api(monkeypatch)
    monkeypatch.delenv("CLOUDFLARE_AI_API_TOKEN")
    assert main(DRAIN) == 2
    token_err = capsys.readouterr().err
    monkeypatch.setenv("CLOUDFLARE_AI_API_TOKEN", TOKEN)
    monkeypatch.setenv("LLM_MODEL", "")
    assert main(DRAIN) == 2
    model_err = capsys.readouterr().err
    monkeypatch.setenv("LLM_MODEL", "@cf/acme/mystery-model")
    assert main(DRAIN) == 2
    price_err = capsys.readouterr().err

    assert "CLOUDFLARE_AI_API_TOKEN" in token_err and ACCOUNT_ID not in token_err
    assert "LLM_MODEL" in model_err and "mystery-model" in price_err
    assert _nothing_was_claimed(api)


def test_a_drain_without_a_neuron_budget_fails_before_claiming(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """worker drain · llm_extract with no --neuron-budget exits 2 and claims nothing."""
    api = _api(monkeypatch)

    assert main(["worker", "drain", "--kinds", "llm_extract"]) == 2

    assert "neuron_budget" in capsys.readouterr().err and _nothing_was_claimed(api)


@pytest.mark.parametrize("problem", ["ledger", "storage_off", "storage_error", "taxonomy"])
def test_a_drain_with_an_unreadable_ledger_taxonomy_or_missing_storage_fails_before_claiming(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], problem: str
) -> None:
    """worker drain · no readable ledger, no storage or no taxonomy exits 1 with a clear message, nothing claimed."""
    api = _api(monkeypatch)
    match problem:
        case "ledger":
            api.ledger_remaining = None
        case "storage_off":
            api.storage_enabled = False
        case "storage_error":
            api.status_http = 500
        case _:
            api.taxonomy_status = 404

    code = main(DRAIN)

    word = {"ledger": "ledger", "storage_off": "storage", "storage_error": "storage", "taxonomy": "taxonomy"}[problem]
    assert code == 1 and word in capsys.readouterr().err and _nothing_was_claimed(api)


def test_the_drain_report_includes_neurons_calls_released_and_the_llm_stop_reasons(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """worker drain · a page shows neurons_used and llm_calls; a spent day shows released and stop llm_quota."""
    api = _api(monkeypatch)
    assert main(DRAIN) == 0
    done = json.loads(capsys.readouterr().out)
    assert (done["completed"], done["llm_calls"], done["released"], done["stop_reason"]) == (1, 1, 0, "batch_limit")
    assert done["neurons_used"] == pytest.approx(cost(MODEL, 1000, 200), abs=0.1)
    assert api.edge_posts and api.finishes[0]["status"] == "succeeded"

    limited = _api(monkeypatch, tasks=3)
    limited.cloudflare = lambda request: failure(429, 4006, "you have used up your daily free allocation")
    assert main(DRAIN) == 0
    stopped = json.loads(capsys.readouterr().out)
    assert (stopped["stop_reason"], stopped["released"], stopped["succeeded"]) == ("llm_quota", 3, True)
    assert limited.ledger_exhausted and limited.finishes[0]["stop_reason"] == "llm_quota"


def test_a_rejected_ai_token_fails_the_run_and_the_command(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """worker drain · a 401 from Workers AI releases the batch, records a failed run, exits 1 and never prints the token."""
    api = _api(monkeypatch, tasks=2)
    api.cloudflare = lambda request: failure(401, 10000, "Authentication error")

    code = main(DRAIN)

    report = json.loads(capsys.readouterr().out)
    assert code == 1 and (report["succeeded"], report["stop_reason"], report["released"]) == (False, "error", 2)
    assert api.finishes[0]["status"] == "failed" and TOKEN not in json.dumps(report) + str(api.finishes)
