"""``llm eval``: the gold set through the cleaner, a fake model and grounding, under the ledger (chapter E5, loop B)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from discovery_ingest.cli import main
from discovery_ingest.extract.llm.evaluation import command
from discovery_ingest.extract.llm.evaluation.command import EvalRuntime
from discovery_ingest.extract.llm.prices import cost

from eval_fakes import ANSWERS, MODEL, FakeLlm, write_gold
from ledger_fakes import FakeLedger, guard_for
from llm_fakes import taxonomy
from llm_transport import ACCOUNT_ID, TOKEN


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    for name in ("LLM_MODEL", "LLM_MAX_TOKENS", "LLM_INPUT_CHARS"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DISCOVERY_API_URL", "https://redtape.test")
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", ACCOUNT_ID)
    monkeypatch.setenv("CLOUDFLARE_AI_API_TOKEN", TOKEN)


def _wire(monkeypatch: pytest.MonkeyPatch, llm: FakeLlm, ledger: FakeLedger | None = None) -> FakeLedger:
    ledger = ledger or FakeLedger(remaining=9000)
    guard = guard_for(monkeypatch, ledger)
    monkeypatch.setattr(command, "_runtime", lambda _settings, _model: EvalRuntime(llm, guard, taxonomy()))
    return ledger


def _eval(tmp_path: Path, *extra: str, model: str = MODEL) -> int:
    gold = tmp_path / "gold"
    args = ["llm", "eval", "--model", model, "--gold-dir", str(gold), "--cache-dir", str(tmp_path / "cache")]
    return main([*args, "--out", str(tmp_path / "out.json"), *extra])


def _out(tmp_path: Path) -> dict[str, Any]:
    return json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))


def test_eval_runs_every_gold_page_through_clean_client_and_grounding_and_prints_a_table(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """eval · three pages reach the model (the empty shell does not), items are grounded, the table shows the metrics."""
    write_gold(tmp_path / "gold")
    llm = FakeLlm()
    _wire(monkeypatch, llm)

    code = _eval(tmp_path)

    shown = capsys.readouterr().out
    summary = _out(tmp_path)["summary"]
    assert code == 0 and sorted(llm.calls) == ["BundID", "Neuigkeiten", "Reisepass"]
    assert all(name in shown for name in ("alpha", "beta", "gamma", "shell"))
    assert all(
        label in shown for label in ("precision", "recall", "grounded rate", "tag agreement", "neurons per page")
    )
    assert (summary["precision"], summary["recall"], summary["grounded_rate"]) == (1.0, 0.5, 0.5)
    assert summary["tag_agreement"] == 1.0 and summary["pages_run"] == 4
    assert summary["neurons_per_page"] == pytest.approx(cost(MODEL, 1000, 200))
    assert (summary["input_tokens"], summary["output_tokens"]) == (3000, 600)


def test_a_page_the_model_answers_badly_is_a_failed_page_not_a_crash_and_an_unpriced_model_is_refused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """eval · invalid JSON scores as nothing found and the run goes on; a model without a price exits 2 before any call."""
    write_gold(tmp_path / "gold", names=["alpha", "gamma"])
    llm = FakeLlm({**ANSWERS, "Reisepass": "this is not json"})
    _wire(monkeypatch, llm)

    assert _eval(tmp_path) == 0
    pages = {page["name"]: page for page in _out(tmp_path)["pages"]}
    assert pages["alpha"]["status"] == "invalid_output" and pages["gamma"]["status"] == "ok"
    assert _out(tmp_path)["summary"]["recall"] == 0.0 and _out(tmp_path)["summary"]["failed_pages"] == 1

    llm.calls.clear()
    assert _eval(tmp_path, model="@cf/acme/mystery") == 2
    assert "mystery" in capsys.readouterr().err and llm.calls == []


def test_limit_keeps_the_first_pages_by_name(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """eval --limit · only the first N gold pages run."""
    write_gold(tmp_path / "gold")
    llm = FakeLlm()
    _wire(monkeypatch, llm)

    assert _eval(tmp_path, "--limit", "1") == 0
    assert [page["name"] for page in _out(tmp_path)["pages"]] == ["alpha"] and llm.calls == ["Reisepass"]
