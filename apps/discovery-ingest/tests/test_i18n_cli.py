"""``i18n translate-ui``: the real engine over a mock Workers AI, the neuron ledger and the files of a scratch repository (search-first C11)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from discovery_ingest.cli import main

from azure_transport import faithful_answer
from ledger_fakes import CHARACTERS_CAP, FakeLedger
from llm_transport import ACCOUNT_ID, TOKEN, failure, success
from translate_fakes import TranslateApi

SEED = Path("apps/api/scripts/seed_data/translations")
WEB = Path("apps/web/src/i18n/fallback")
EN = {"common": {"save": "Save", "cancel": "Cancel"}, "n_one": "{count} item", "n_other": "{count} items"}
DE = {"common": {"save": "Speichern", "cancel": "Abbrechen"}, "n_one": "{count} Eintrag", "n_other": "{count} Einträge"}
CATEGORY = {
    "code": "housing",
    "name_i18n": {"de": "Wohnen", "en": "Housing"},
    "description_i18n": {"de": "Mieten und Umziehen.", "en": "Renting and moving."},
}


class UiApi(TranslateApi):
    """The machine API with the taxonomy route the command reads the categories from."""

    taxonomy_down = False

    def _taxonomy(self, _body: dict[str, Any]) -> httpx.Response:
        if self.taxonomy_down:
            return httpx.Response(503, json={"detail": "unavailable"})
        return httpx.Response(200, json={"categories": [CATEGORY]})


@pytest.fixture
def repo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    for folder in (SEED, WEB):
        (tmp_path / folder).mkdir(parents=True)
    (tmp_path / SEED / "en.json").write_text(json.dumps(EN), encoding="utf-8")
    (tmp_path / SEED / "de.json").write_text(json.dumps(DE), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DISCOVERY_API_URL", "https://redtape.test")
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", ACCOUNT_ID)
    monkeypatch.setenv("CLOUDFLARE_AI_API_TOKEN", TOKEN)
    monkeypatch.setenv("LLM_MODEL", "@cf/qwen/qwen3-30b-a3b-fp8")
    monkeypatch.setattr("discovery_ingest.operations.translate_ui.UI_MIN_INTERVAL_SECONDS", 0.0)
    yield tmp_path


def _answer(request: httpx.Request) -> httpx.Response:
    units = json.loads(json.loads(request.content)["messages"][-1]["content"])["units"]
    body = {"units": [{"key": u["key"], "title": f"[xx] {u['title']}", "description": ""} for u in units]}
    return success(body, {"prompt_tokens": 100, "completion_tokens": 60, "neurons": 3.0})


def _run(monkeypatch: pytest.MonkeyPatch, api: UiApi, cloudflare=_answer, *argv: str) -> int:  # noqa: ANN001
    api.install(monkeypatch, cloudflare)
    return main(["i18n", "translate-ui", "--locale", "tr", "--repo-root", ".", *argv])


def test_the_command_translates_writes_the_files_and_records_a_machine_manifest_entry(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], repo: Path
) -> None:
    """translate-ui · one JSON report; seed file, web mirror, taxonomy module and review.json are written; no secret printed."""
    api = UiApi([])

    code = _run(monkeypatch, api)

    out = capsys.readouterr().out
    report = json.loads(out)
    assert code == 0 and (report["locale"], report["translated"], report["stopped"]) == ("tr", 6, None)
    assert report["neurons"] == 3.0 and report["rejected"] == []
    assert (repo / SEED / "tr.json").read_bytes() == (repo / WEB / "tr.json").read_bytes()
    assert "Konut" not in out and "[xx] Wohnen" in (
        repo / "apps/api/scripts/seed_data/taxonomy_translations.py"
    ).read_text(encoding="utf-8")
    entry = json.loads((repo / SEED / "review.json").read_text(encoding="utf-8"))["locales"]["tr"]
    assert (entry["status"], entry["model"]) == ("machine", "@cf/qwen/qwen3-30b-a3b-fp8")
    assert TOKEN not in out and ACCOUNT_ID not in out and "test-machine-key" not in out


def test_the_spend_goes_through_the_shared_ledger(monkeypatch: pytest.MonkeyPatch, repo: Path) -> None:
    """translate-ui · every Workers AI call reserves from and settles with the neuron ledger."""
    api = UiApi([])

    _run(monkeypatch, api)

    actions = [action for action, _body in api.ledger.calls]
    assert "reserve" in actions and "adjust" in actions
    assert api.ledger.remaining < 9000.0


@pytest.mark.parametrize("locale", ["de", "en", "fr"])
def test_a_locale_that_is_not_a_ui_target_exits_2_before_any_request(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], repo: Path, locale: str
) -> None:
    """translate-ui · only tr, ru, uk, pl and ro are generated; anything else is a usage error."""
    api = UiApi([])
    api.install(monkeypatch)

    assert main(["i18n", "translate-ui", "--locale", locale, "--repo-root", "."]) == 2
    assert "tr, ru, uk, pl, ro" in capsys.readouterr().err and not api.ledger.calls
    assert not (repo / SEED / "review.json").exists() and not (repo / SEED / "fr.json").exists()


def test_a_quota_stop_exits_3_with_the_partial_files_and_a_rerun_continues(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], repo: Path
) -> None:
    """translate-ui · the allowance is gone after one batch: exit 3, the finished batch is on disk, a rerun finishes."""
    calls: list[int] = []

    def quota_second_time(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 2:
            return failure(429, 4006, "you have used up your daily free allocation")
        return _answer(request)

    api = UiApi([])

    code = _run(monkeypatch, api, quota_second_time, "--batch-size", "2")

    report = json.loads(capsys.readouterr().out)
    assert code == 3 and report["stopped"] == "llm_quota" and report["remaining"] == 4
    assert len(json.loads((repo / SEED / "tr.json").read_text(encoding="utf-8"))) >= 1
    api.ledger.exhausted = False
    assert _run(monkeypatch, api, _answer, "--batch-size", "2") == 0


def test_a_string_the_model_cannot_get_right_exits_1_and_is_reported(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], repo: Path
) -> None:
    """translate-ui · a placeholder that never comes back is rejected after one repair; the key stays absent; exit 1."""

    def drop_placeholder(request: httpx.Request) -> httpx.Response:
        response = _answer(request)
        return httpx.Response(200, content=response.content.replace(b"{count}", b""))

    api = UiApi([])

    code = _run(monkeypatch, api, drop_placeholder)

    report = json.loads(capsys.readouterr().out)
    assert code == 1 and {r["key"] for r in report["rejected"]} == {"n_one", "n_other"}
    assert "n_one" not in json.loads((repo / SEED / "tr.json").read_text(encoding="utf-8"))


def test_a_floor_that_leaves_nothing_to_spend_stops_before_the_first_call(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], repo: Path
) -> None:
    """translate-ui · the neurons kept for query embedding are never spent: below the floor, exit 3, no model call."""
    monkeypatch.setenv("QUERY_EMBED_RESERVE", "8999")
    api = UiApi([])
    api.ledger.remaining = 9000.0
    seen: list[httpx.Request] = []

    def spy(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _answer(request)

    code = _run(monkeypatch, api, spy, "--neuron-budget", "500")

    assert code == 3 and api.ledger.remaining >= 8999.0
    assert json.loads(capsys.readouterr().out)["stopped"] in {"llm_budget"}


def test_an_unreadable_taxonomy_refuses_to_start_before_any_model_call(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], repo: Path
) -> None:
    """translate-ui · the categories come from the machine API; without them the run exits 1 and spends nothing."""
    api = UiApi([])
    api.taxonomy_down = True

    code = _run(monkeypatch, api)

    assert code == 1 and "taxonomy" in capsys.readouterr().err
    assert not any(action == "reserve" for action, _body in api.ledger.calls)


def test_an_azure_translator_run_is_accepted_with_a_character_meter_and_reports_what_it_billed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], repo: Path
) -> None:
    """Translate-ui · an azure-translator run is accepted with a character meter (no exit 2)."""
    monkeypatch.setenv("TRANSLATION_ENGINE", "azure-translator")
    monkeypatch.setenv("AZURE_TRANSLATOR_KEY", "azure-key-SECRET-0123456789")
    monkeypatch.setenv("AZURE_TRANSLATOR_REGION", "westeurope")
    api = UiApi([], ledger=FakeLedger(9000.0, characters=float(CHARACTERS_CAP)))
    api.install(monkeypatch, azure=faithful_answer)

    code = main(["i18n", "translate-ui", "--locale", "tr", "--repo-root", "."])

    report = json.loads(capsys.readouterr().out)
    assert code == 0 and report["translated"] == 6
    assert report["neurons"] == 0.0 and report["characters_used"] > 0
    assert (
        api.ledger.characters is not None
        and api.ledger.characters.remaining == CHARACTERS_CAP - report["characters_used"]
    )
    assert api.ledger.writes_to("neurons") == []
