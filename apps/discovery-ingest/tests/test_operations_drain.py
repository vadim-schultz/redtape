"""Drain operations · options become a validated policy; run_drain returns the report and prints nothing."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.config import load_ingest_settings
from discovery_ingest.operations.drain import LLM_BATCH_SIZE, DrainOptions, run_drain
from discovery_ingest.worker.policy import MAX_TASKS_PER_CLAIM

from run_stub import run_response

API_BASE = "https://redtape.test"
_REAL_HTTPX_CLIENT = httpx.Client


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCOVERY_API_URL", API_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")
    for name in ("CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_BROWSER_API_TOKEN", "CLOUDFLARE_AI_API_TOKEN", "LLM_MODEL"):
        monkeypatch.delenv(name, raising=False)


def _empty_claim_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        stub = run_response(request)
        if stub is not None:
            return stub
        if str(request.url).endswith("/tasks/claim"):
            return httpx.Response(200, json={"items": []})
        if str(request.url).endswith("/tasks/summary"):
            return httpx.Response(200, json={"pending_ready": 0})
        return httpx.Response(200, json={"remaining": 0, "limit": 0, "used": 0, "ledger": "ok"})

    transport = httpx.MockTransport(handler)

    def client_factory(**kwargs: Any) -> httpx.Client:
        kwargs["transport"] = transport
        return _REAL_HTTPX_CLIENT(**kwargs)

    monkeypatch.setattr("discovery_ingest.client.http_client.httpx.Client", client_factory)
    monkeypatch.setattr("discovery_ingest.worker.fetcher.httpx.Client", client_factory)


def test_drain_options_policy_uses_the_default_claim_size_for_plain_kinds() -> None:
    """DrainOptions · without llm_extract the default claim size is the plain 50."""
    assert DrainOptions().policy().max_tasks == MAX_TASKS_PER_CLAIM


def test_drain_options_policy_uses_llm_batch_size_when_llm_extract_is_drained() -> None:
    """DrainOptions · draining llm_extract defaults the claim size to the llm batch size."""
    options = DrainOptions(kinds=("llm_extract",), neuron_budget=1.0, browser_budget_seconds=None)

    assert options.policy().max_tasks == LLM_BATCH_SIZE == 5


def test_drain_options_explicit_max_tasks_wins_over_the_llm_default() -> None:
    """DrainOptions · an explicit claim size is kept as given."""
    options = DrainOptions(kinds=("llm_extract",), max_tasks=3, neuron_budget=1.0, browser_budget_seconds=None)

    assert options.policy().max_tasks == 3


@pytest.mark.parametrize(
    "options",
    [
        DrainOptions(max_tasks=0),
        DrainOptions(max_tasks=51),
        DrainOptions(max_batches=0),
        DrainOptions(kinds=("llm_extract",), browser_budget_seconds=None),
    ],
)
def test_drain_options_invalid_bounds_raise_value_error(options: DrainOptions) -> None:
    """DrainOptions · an out-of-range bound, or a drained llm kind without its neuron budget, raises ValueError."""
    with pytest.raises(ValueError):
        options.policy()


def test_run_drain_returns_the_report_and_prints_nothing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """run_drain · returns the recorded report and writes nothing to stdout or stderr."""
    _empty_claim_transport(monkeypatch)
    settings = load_ingest_settings()

    with DiscoveryIngestClient.from_settings(settings) as client:
        report = run_drain(DrainOptions(browser_budget_seconds=570.0), settings, client)

    assert report.stop_reason == "queue_empty"
    assert report.succeeded is True
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("module", ["drain", "models", "catalogue", "enrich", "results"])
def test_operations_modules_import_no_cli_or_output_library(module: str) -> None:
    """operations · no operation module imports argparse, typer, rich or sys."""
    import ast
    from pathlib import Path

    source = Path(__file__).parents[1] / "discovery_ingest" / "operations" / f"{module}.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not imported & {"argparse", "typer", "rich", "sys"}
