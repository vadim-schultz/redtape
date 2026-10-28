"""``llm eval``: the gold set through the cleaner, a fake model and grounding, under the ledger (chapter E5, loop B)."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from discovery_ingest.cli import main
from discovery_ingest.extract.llm.errors import LlmAuthError, LlmQuotaExceeded, LlmRequestError
from discovery_ingest.extract.llm.evaluation import command
from discovery_ingest.extract.llm.evaluation.command import EvalRuntime
from discovery_ingest.extract.llm.prices import cost
from discovery_ingest.extract.llm.taxonomy import Taxonomy

from eval_fakes import ANSWERS, MODEL, PAGES, FakeLlm, write_gold
from ledger_fakes import FakeLedger, guard_for
from llm_fakes import taxonomy
from llm_transport import ACCOUNT_ID, TOKEN, failure, success


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    for name in ("LLM_MODEL", "LLM_MAX_TOKENS", "LLM_INPUT_CHARS"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DISCOVERY_API_URL", "https://redtape.test")
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", ACCOUNT_ID)
    monkeypatch.setenv("CLOUDFLARE_AI_API_TOKEN", TOKEN)


def _wire(
    monkeypatch: pytest.MonkeyPatch, llm: FakeLlm, ledger: FakeLedger | None = None, vocabulary: Taxonomy | None = None
) -> FakeLedger:
    ledger = ledger or FakeLedger(remaining=9000)
    guard = guard_for(monkeypatch, ledger)
    runtime = EvalRuntime(llm, guard, vocabulary or taxonomy())
    monkeypatch.setattr(command, "_runtime", lambda _settings, _model: runtime)
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


def test_eval_reserves_from_the_ledger_and_stops_with_a_clear_message_when_the_budget_is_spent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """eval · each call reserves first and settles after; the next page past the run budget ends the run, kept results stay."""
    write_gold(tmp_path / "gold", names=["alpha", "beta", "gamma"])
    llm = FakeLlm()
    ledger = _wire(monkeypatch, llm)

    code = _eval(tmp_path, "--neuron-budget", "160")

    report = _out(tmp_path)
    shown = capsys.readouterr().out
    assert code == 1 and llm.calls == ["Reisepass"]
    assert ledger.actions()[:3] == ["budgets", "reserve", "adjust"]
    assert ledger.remaining == pytest.approx(9000 - cost(MODEL, 1000, 200))
    assert [page["name"] for page in report["pages"]] == ["alpha"] and report["stopped"]["reason"] == "budget"
    assert "neuron budget of 160 is spent" in shown and "pages run 1 of 3" in shown


def test_eval_refuses_to_start_when_the_day_is_spent_or_the_ledger_cannot_be_read(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """eval · an exhausted day and an unreachable ledger both exit 1 before any model call and write no file."""
    write_gold(tmp_path / "gold", names=["alpha"])
    llm = FakeLlm()
    _wire(monkeypatch, llm, FakeLedger(remaining=0, exhausted=True))
    assert _eval(tmp_path) == 1
    assert "no neurons are left today" in capsys.readouterr().err

    _wire(monkeypatch, llm, FakeLedger(remaining=9000, down=True))
    assert _eval(tmp_path) == 1
    assert "ledger is unreachable" in capsys.readouterr().err
    assert llm.calls == [] and not (tmp_path / "out.json").exists()


def test_a_provider_quota_error_marks_the_day_exhausted_and_a_rejected_token_stops_the_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """eval · LlmQuotaExceeded tells the ledger and stops with llm_quota; LlmAuthError stops with llm_auth."""
    write_gold(tmp_path / "gold", names=["alpha", "gamma"])
    quota = FakeLlm({**ANSWERS, "Reisepass": LlmQuotaExceeded("daily free allocation used up")})
    ledger = _wire(monkeypatch, quota)

    assert _eval(tmp_path) == 1
    assert "exhaust" in ledger.actions() and _out(tmp_path)["stopped"]["reason"] == "llm_quota"
    assert "daily free allocation used up" in capsys.readouterr().out

    denied = FakeLlm({**ANSWERS, "Reisepass": LlmAuthError("Cloudflare HTTP 403")})
    ledger = _wire(monkeypatch, denied)
    assert _eval(tmp_path) == 1
    assert "exhaust" not in ledger.actions() and _out(tmp_path)["stopped"]["reason"] == "llm_auth"


REAL_TAXONOMY = Path(__file__).parent / "fixtures" / "gold" / "taxonomy.json"
BIG_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"


def test_a_cached_page_is_not_sent_again_for_the_same_model_prompt_and_cleaner_version(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """eval · a second run answers every page from the cache: no model call, no reservation, same scores and cost."""
    write_gold(tmp_path / "gold", names=["alpha", "gamma"])
    llm = FakeLlm()
    ledger = _wire(monkeypatch, llm)
    assert _eval(tmp_path) == 0
    first = _out(tmp_path)
    reserved = ledger.actions().count("reserve")

    assert _eval(tmp_path) == 0

    second = _out(tmp_path)
    assert llm.calls == ["Reisepass", "Neuigkeiten"] and ledger.actions().count("reserve") == reserved
    assert [page["cached"] for page in second["pages"]] == [True, True] and second["neurons_used"] == 0
    assert second["summary"]["precision"] == first["summary"]["precision"]
    assert second["summary"]["neurons_per_page"] == pytest.approx(first["summary"]["neurons_per_page"])


def test_a_new_model_a_changed_page_or_a_damaged_cache_file_is_sent_again(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """eval · the cache is keyed by model and page text; an unreadable entry is a miss, never a crash."""
    gold = write_gold(tmp_path / "gold", names=["alpha", "gamma"])
    llm = FakeLlm()
    _wire(monkeypatch, llm)
    assert _eval(tmp_path) == 0
    llm.calls.clear()

    assert _eval(tmp_path, model=BIG_MODEL) == 0
    assert llm.calls == ["Reisepass", "Neuigkeiten"]

    llm.calls.clear()
    (gold / "gamma.html").write_text(PAGES["gamma"].replace("Neuigkeiten", "Neuigkeiten und mehr"), encoding="utf-8")
    assert _eval(tmp_path) == 0
    assert llm.calls == ["Neuigkeiten"]

    llm.calls.clear()
    for entry in (tmp_path / "cache").glob("*.json"):
        entry.write_text("{not json", encoding="utf-8")
    assert _eval(tmp_path) == 0
    assert llm.calls == ["Reisepass", "Neuigkeiten"]


def test_the_output_file_lists_dropped_items_with_their_reasons(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """eval --out · a quote that is not on the page and items on a login page are listed with a reason; clean pages list none."""
    write_gold(tmp_path / "gold", names=["alpha", "beta", "gamma"])
    login_with_item = {
        **ANSWERS["BundID"],
        "documents": [{"name": "BundID-Konto", "role": "required", "quote": "mit BundID an"}],
    }
    _wire(monkeypatch, FakeLlm({**ANSWERS, "BundID": login_with_item}))

    assert _eval(tmp_path) == 0

    pages = {page["name"]: page for page in _out(tmp_path)["pages"]}
    phantom = pages["alpha"]["dropped"]
    assert [(item["reason"], item["kind"], item["item"]["name"]) for item in phantom] == [
        ("quote", "document", "Phantom")
    ]
    assert phantom[0]["item"]["quote"] == "this sentence is not on the page"
    assert [(item["reason"], item["item"]["name"]) for item in pages["beta"]["dropped"]] == [
        ("page_kind", "BundID-Konto")
    ]
    assert pages["gamma"]["dropped"] == []
    assert (pages["beta"]["raw_items"], pages["beta"]["kept_items"]) == (1, 0)


def _router(monkeypatch: pytest.MonkeyPatch, ledger: FakeLedger, cloudflare: Callable[[str], httpx.Response]) -> None:
    """Serve the machine API (taxonomy and ledger) and Cloudflare from one mock transport, behind the real wiring."""
    real_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "redtape.test" and request.url.path.endswith("/taxonomy"):
            return httpx.Response(200, json=taxonomy().model_dump(mode="json"))
        if request.url.host == "redtape.test":
            return ledger(request)
        return cloudflare(request.content.decode())

    monkeypatch.setattr("time.sleep", lambda _seconds: None)
    monkeypatch.setattr(httpx, "Client", lambda **kw: real_client(**{**kw, "transport": httpx.MockTransport(handler)}))


def _answer(body: str) -> httpx.Response:
    marker = next(marker for marker in ANSWERS if marker in body)
    return success(ANSWERS[marker], {"prompt_tokens": 1000, "completion_tokens": 200})


def test_eval_never_prints_the_token_or_the_account_id_even_when_cloudflare_echoes_them(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """eval · through the real client and taxonomy route, neither the table, stderr nor the JSON holds a credential."""
    write_gold(tmp_path / "gold", names=["alpha", "gamma"])
    echo = failure(400, 1000, f"bad request for {TOKEN} on account {ACCOUNT_ID}")
    _router(monkeypatch, FakeLedger(remaining=9000), lambda body: echo if "Neuigkeiten" in body else _answer(body))

    assert _eval(tmp_path) == 0

    shown = capsys.readouterr()
    written = (tmp_path / "out.json").read_text(encoding="utf-8")
    pages = {page["name"]: page for page in json.loads(written)["pages"]}
    assert pages["alpha"]["status"] == "ok" and pages["gamma"]["status"] == "request_error"
    assert "<redacted>" in pages["gamma"]["error"]
    for secret in (TOKEN, ACCOUNT_ID):
        assert secret not in shown.out + shown.err + written


def test_a_credential_inside_an_error_text_is_scrubbed_at_the_command_even_when_the_client_did_not(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """eval · defense in depth: a client that leaks the token in its error still cannot reach the output."""
    write_gold(tmp_path / "gold", names=["gamma"])
    leaky = FakeLlm({**ANSWERS, "Neuigkeiten": LlmRequestError(f"connect failed with {TOKEN}", retryable=True)})
    _wire(monkeypatch, leaky)

    assert _eval(tmp_path) == 0

    shown = capsys.readouterr()
    written = (tmp_path / "out.json").read_text(encoding="utf-8")
    assert TOKEN not in shown.out + shown.err + written and "<redacted>" in written


def test_the_committed_real_gold_set_runs_end_to_end_and_reports_the_offline_cleaner_recall(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """eval · with no --gold-dir the 20 real pages run; the empty shell is not sent; a silent model scores recall 0."""
    silent = {"page_kind": "other", "domain_codes": [], "situation_codes": [], "documents": [], "dependencies": []}
    llm = FakeLlm({"<page>": silent})
    _wire(monkeypatch, llm, vocabulary=Taxonomy.model_validate_json(REAL_TAXONOMY.read_text(encoding="utf-8")))

    code = main(
        ["llm", "eval", "--model", MODEL, "--cache-dir", str(tmp_path / "cache"), "--out", str(tmp_path / "out.json")]
    )

    summary = _out(tmp_path)["summary"]
    assert code == 0 and summary["pages_run"] == 20 and len(llm.calls) == 19
    assert (summary["recall"], summary["precision"], summary["failed_pages"]) == (0.0, 1.0, 0)
    assert summary["cleaner_recall"] == pytest.approx(44 / 47)
