"""translate probe: pass rate, usage per unit and projected corpus cost from canned responses; nothing is written but the sheet."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import httpx
import pytest
from discovery_ingest.cli import main
from discovery_ingest.translation.adapters.cloudflare_llm import LlmTranslator
from discovery_ingest.translation.glossary import load_glossary
from discovery_ingest.translation.probe import ProbeOptions, run_probe
from discovery_ingest.translation.probe_sample import (
    Corpus,
    ProbeSourceError,
    PublicCandidateReader,
    pick_sample,
)
from discovery_ingest.translation.units import TranslationUnit

from llm_transport import ACCOUNT_ID, MODEL, TOKEN, client, failure, success

CORPUS_TOTAL = 4000
USAGE_PER_CALL = {"prompt_tokens": 400, "completion_tokens": 300, "neurons": 10.0}


def _corpus(count: int = 12, total: int = CORPUS_TOTAL) -> Corpus:
    units = tuple(
        TranslationUnit(f"id-{index:03d}", f"Bescheinigung Nr. {index}", f"Gebühr {index} Euro pro Jahr")
        for index in range(count)
    )
    return Corpus(units=units, total=total)


def _en(text: str) -> str:
    """A canned English rendering that follows the glossary and keeps every number."""
    return "[en] " + text.replace("Bescheinigung", "certificate").replace("Gebühr", "fee")


def _units_in(request: httpx.Request) -> list[dict[str, str]]:
    return json.loads(json.loads(request.content)["messages"][-1]["content"])["units"]


def _faithful(request: httpx.Request) -> httpx.Response:
    units = _units_in(request)
    answer = {
        "units": [{"key": u["key"], "title": _en(u["title"]), "description": _en(u["description"])} for u in units]
    }
    return success(answer, USAGE_PER_CALL)


def _options(**overrides: object) -> ProbeOptions:
    fields: dict[str, object] = {
        "locale": "en",
        "glossary": load_glossary("en"),
        "sample": 10,
        "batch_size": 5,
        "max_usage": 10_000.0,
        "daily_budget": 8000.0,
        "target_count": 6,
    }
    return ProbeOptions(**{**fields, **overrides})  # type: ignore[arg-type]


def _engine(handler: object) -> LlmTranslator:
    return LlmTranslator(client(handler), model=MODEL, max_tokens=2000)  # type: ignore[arg-type]


def test_the_probe_reports_pass_rate_usage_per_unit_and_the_projected_corpus_cost() -> None:
    """probe · reports pass rate, neurons per unit and projected corpus cost from canned responses."""
    result = run_probe(_engine(_faithful), _corpus(), _options())
    report = result.report

    assert (report.sample_size, report.translated, report.validated_ok, report.pass_rate) == (10, 10, 10, 1.0)
    assert (report.usage_unit, report.usage_total, report.usage_per_unit) == ("neurons", 20.0, 2.0)
    assert report.projected_usage_locale == 8000.0
    assert report.projected_usage_all_locales == 48000.0 and report.target_locales == 6
    assert report.days_at_daily_budget == 6.0
    assert report.batches == 2 and report.latency_ms_per_batch is not None
    assert report.engine == "llm" and report.model == MODEL and report.stopped is None


def test_a_sample_that_fails_validation_is_reported_with_its_findings_and_not_dropped() -> None:
    """probe · units that fail validation are counted, listed with their checks and kept in the sheet."""

    def changes_a_number(request: httpx.Request) -> httpx.Response:
        units = _units_in(request)
        answer = {
            "units": [
                {"key": u["key"], "title": _en(u["title"]), "description": _en(u["description"]).replace("1", "7")}
                for u in units
            ]
        }
        return success(answer, USAGE_PER_CALL)

    result = run_probe(_engine(changes_a_number), _corpus(), _options())
    report = result.report

    assert report.translated == 10 and report.validated_ok < 10 and report.pass_rate < 1.0
    assert report.failures["numbers"] == 10 - report.validated_ok
    assert {failed.key for failed in report.failed} == {row.key for row in result.rows if row.findings}
    assert len(result.rows) == 20 and any("numbers" in row.findings for row in result.rows)


def test_an_unusable_batch_is_reported_as_failed_units_and_the_probe_goes_on() -> None:
    """probe · a batch the model answered unusably counts its units as failed (no translation), not as skipped."""
    calls: list[int] = []

    def short_then_fine(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return success({"units": []}, USAGE_PER_CALL)
        return _faithful(request)

    report = run_probe(_engine(short_then_fine), _corpus(), _options()).report

    assert report.translated == 5 and report.validated_ok == 5 and report.unusable_units == 5
    assert report.pass_rate == 0.5


def test_a_quota_error_stops_the_probe_with_a_reason_and_keeps_what_was_translated() -> None:
    """probe · a quota error ends the probe with a stop reason; the finished batches stay in the report."""
    calls: list[int] = []

    def quota_on_second(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 2:
            return failure(429, 4006, f"you have used up your daily free allocation {TOKEN}")
        return _faithful(request)

    report = run_probe(_engine(quota_on_second), _corpus(), _options()).report

    assert report.translated == 5 and report.stopped is not None and "QuotaExceeded" in report.stopped
    assert TOKEN not in report.model_dump_json()


def test_the_probe_stops_when_the_usage_cap_is_reached() -> None:
    """probe · max_usage bounds what the probe may spend: it stops after the batch that reaches the cap."""
    report = run_probe(_engine(_faithful), _corpus(), _options(max_usage=10.0)).report

    assert report.batches == 1 and report.stopped is not None and "max usage" in report.stopped


def test_the_sheet_lists_german_and_translation_side_by_side(tmp_path: Path) -> None:
    """probe · the spot-check sheet has the German text, the translation, the findings and an empty reviewer column."""
    from discovery_ingest.translation.probe_sheet import write_sheet  # noqa: PLC0415

    result = run_probe(_engine(_faithful), _corpus(), _options(sample=2))
    path = write_sheet(result.rows, tmp_path / "out" / "llm-en.csv")

    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    assert list(rows[0]) == ["key", "field", "german", "translation", "findings", "reviewer_note"]
    assert (rows[0]["field"], rows[0]["translation"]) == ("title", _en(rows[0]["german"]))
    assert rows[0]["german"].startswith("Bescheinigung Nr. ")
    assert rows[1]["field"] == "description" and rows[0]["reviewer_note"] == ""
    assert len(rows) == 4


def test_the_sample_is_fixed_and_reproducible_whatever_the_order_of_the_corpus() -> None:
    """probe · the same corpus yields the same sample, also when the API returns it in another order."""
    corpus = _corpus(40)

    first = pick_sample(corpus.units, 8)
    second = pick_sample(tuple(reversed(corpus.units)), 8)

    assert first == second and len(first) == 8 and len({u.key for u in first}) == 8
    assert pick_sample(corpus.units, 100) == tuple(sorted(corpus.units, key=lambda u: u.key))


def _candidates_transport(pages: dict[int, list[dict[str, object]]], total: int) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/candidates/" and request.url.params["locale"] == "de"
        offset = int(request.url.params["offset"])
        return httpx.Response(
            200, json={"items": pages.get(offset, []), "total": total, "offset": offset, "limit": 100}
        )

    return httpx.MockTransport(handler)


def _card(index: int, description: str | None = "Beschreibung") -> dict[str, object]:
    return {"id": f"id-{index}", "title": f"Titel {index}", "description": description}


def test_the_reader_pages_through_the_public_list_and_maps_cards_to_units() -> None:
    """probe · the reader reads every page of the public candidate list in German and returns the total."""
    pages = {0: [_card(i) for i in range(100)], 100: [_card(100, None)]}
    reader = PublicCandidateReader("https://api.example/", httpx.Client(transport=_candidates_transport(pages, 101)))

    corpus = reader.read()

    assert corpus.total == 101 and len(corpus.units) == 101
    assert corpus.units[100] == TranslationUnit("id-100", "Titel 100", "")


def test_the_reader_raises_a_typed_error_when_the_api_refuses() -> None:
    """probe · an API error is a ProbeSourceError naming the status, not an empty corpus."""
    transport = httpx.MockTransport(lambda _request: httpx.Response(503, json={"detail": "down"}))

    with pytest.raises(ProbeSourceError, match="503"):
        PublicCandidateReader("https://api.example", httpx.Client(transport=transport)).read()


@pytest.fixture
def cli_world(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Environment, a routed mock transport for both the candidate list and Workers AI, and no throttling."""
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", ACCOUNT_ID)
    monkeypatch.setenv("CLOUDFLARE_AI_API_TOKEN", TOKEN)
    monkeypatch.setenv("DISCOVERY_API_URL", "https://api.example")
    monkeypatch.setattr("discovery_ingest.operations.translate_probe.PROBE_MIN_INTERVAL_SECONDS", 0.0)
    pages = {0: [_card(i) for i in range(30)]}
    candidates = _candidates_transport(pages, 30)

    def route(request: httpx.Request) -> httpx.Response:
        return _faithful(request) if "/ai/run/" in request.url.path else candidates.handler(request)

    real_client = httpx.Client
    monkeypatch.setattr(
        "discovery_ingest.operations.translate_probe.httpx.Client",
        lambda **kw: real_client(**{**kw, "transport": httpx.MockTransport(route)}),
    )
    return tmp_path / "sheet.csv"


def test_the_cli_prints_one_json_report_writes_the_sheet_and_never_prints_the_token(
    cli_world: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """probe · python -m discovery_ingest translate probe --locale en --sample 6 --engine llm prints a JSON report and writes the sheet."""
    code = main(["translate", "probe", "--locale", "en", "--sample", "6", "--engine", "llm", "--sheet", str(cli_world)])

    out = capsys.readouterr().out
    report = json.loads(out)
    assert code == 0 and report["pass_rate"] == 1.0 and report["projected_usage_locale"] > 0
    assert report["sheet"] == str(cli_world) and cli_world.exists()
    assert TOKEN not in out and ACCOUNT_ID not in out


def test_the_cli_exits_2_for_a_missing_credential_an_unknown_engine_or_the_german_locale(
    cli_world: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """probe · usage errors exit 2 and name the problem: unknown engine (with the registered names), source locale, missing variable."""
    assert main(["translate", "probe", "--locale", "en", "--sample", "3", "--engine", "deepl"]) == 2
    assert "registered: " in capsys.readouterr().err
    assert main(["translate", "probe", "--locale", "de", "--sample", "3", "--engine", "llm"]) == 2
    assert "de" in capsys.readouterr().err
    monkeypatch.delenv("CLOUDFLARE_AI_API_TOKEN")
    assert main(["translate", "probe", "--locale", "en", "--sample", "3", "--engine", "llm"]) == 2
    err = capsys.readouterr().err
    assert "CLOUDFLARE_AI_API_TOKEN" in err and TOKEN not in err
