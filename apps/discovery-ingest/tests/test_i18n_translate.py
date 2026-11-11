"""The UI translation flow: batches, repair, resume, quota stops and what reaches the files (search-first C11)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from discovery_ingest.i18n.files import Layout, TranslationFiles
from discovery_ingest.i18n.strings import SourceString, taxonomy_key
from discovery_ingest.i18n.translate_ui import UiJob, translate_locale
from discovery_ingest.translation.errors import UnusableOutputError
from discovery_ingest.worker.stop import StopDrain

from ui_fakes import GLOSSARY, MODEL, ScriptedTranslator, prefixed, source

SOURCES = [
    source("common.save", "Save", "Speichern"),
    source("common.cancel", "Cancel", "Abbrechen"),
    source("documents.count_one", "{count} document", "{count} Dokument"),
    source("documents.count_other", "{count} documents", "{count} Dokumente"),
    source("forms.apply", "Fill in the form", "Formular ausfüllen"),
    source(taxonomy_key("housing", "name"), "Housing", "Wohnen"),
    source(taxonomy_key("housing", "description"), "Renting and moving.", "Mieten und Umziehen."),
]


@pytest.fixture
def files(tmp_path: Path) -> TranslationFiles:
    layout = Layout(tmp_path / "seed", tmp_path / "web", tmp_path / "taxonomy_translations.py")
    return TranslationFiles(layout)


def _job(locale: str = "ru", sources: list[SourceString] | None = None, batch_size: int = 40) -> UiJob:
    return UiJob(locale, tuple(sources or SOURCES), GLOSSARY, frozenset(), batch_size)


def _flat(files: TranslationFiles, locale: str = "ru") -> dict[str, str]:
    return files.read(locale)


def test_every_string_is_translated_and_written_to_the_seed_file_the_web_mirror_and_the_taxonomy_module(
    files: TranslationFiles, tmp_path: Path
) -> None:
    """translate · a run writes the nested seed file, the identical web copy and the taxonomy labels."""
    translator = ScriptedTranslator()

    report = translate_locale(_job(), translator, files)

    seed = json.loads((tmp_path / "seed" / "ru.json").read_text(encoding="utf-8"))
    assert seed["common"]["save"] == prefixed("ru", "Speichern")
    assert "housing" not in json.dumps(seed) and "Wohnen" not in json.dumps(seed)
    assert (tmp_path / "web" / "ru.json").read_bytes() == (tmp_path / "seed" / "ru.json").read_bytes()
    assert _flat(files)[taxonomy_key("housing", "name")] == prefixed("ru", "Wohnen")
    assert (report.translated, report.stopped, report.rejected, report.model) == (len(SOURCES) + 2, None, (), MODEL)


def test_the_batch_names_the_source_locale_the_glossary_and_the_key_path_and_english_text_as_context(
    files: TranslationFiles,
) -> None:
    """translate · both sources reach the model: German as the text, English and the key path as context."""
    translator = ScriptedTranslator()

    translate_locale(_job("tr", SOURCES[:1]), translator, files)

    batch = translator.batches[0]
    assert (batch.source_locale, batch.target_locale, batch.glossary) == ("de", "tr", GLOSSARY)
    unit = batch.units[0]
    assert (unit.key, unit.title, unit.description) == ("common.save", "Speichern", "")
    assert "common.save" in unit.context and "Save" in unit.context


def test_the_run_goes_in_batches_of_the_configured_size(files: TranslationFiles) -> None:
    """translate · 7 strings (9 with Russian plural forms) go out in batches of at most 4."""
    translator = ScriptedTranslator()

    translate_locale(_job(batch_size=4), translator, files)

    assert [len(batch.units) for batch in translator.batches] == [4, 4, 1]


def test_a_rerun_skips_the_keys_that_are_present_and_requests_only_the_delta(files: TranslationFiles) -> None:
    """translate · resumes: existing keys are skipped and only the delta is requested."""
    translate_locale(_job(sources=SOURCES[:2]), ScriptedTranslator(), files)
    translator = ScriptedTranslator()

    report = translate_locale(_job(), translator, files)

    assert "common.save" not in translator.asked_keys and "common.cancel" not in translator.asked_keys
    assert report.translated == len(SOURCES) + 2 - 2
    again = ScriptedTranslator()
    assert translate_locale(_job(), again, files).translated == 0 and again.batches == []


def test_a_key_the_source_no_longer_has_is_removed_from_the_locale_file(files: TranslationFiles) -> None:
    """translate · a key dropped from the English copy leaves the locale file at the next run."""
    translate_locale(_job(), ScriptedTranslator(), files)

    translate_locale(_job(sources=SOURCES[:2]), ScriptedTranslator(), files)

    assert set(_flat(files)) == {"common.save", "common.cancel"}


def test_a_failed_string_is_repaired_once_with_the_broken_rules_and_then_accepted(files: TranslationFiles) -> None:
    """translate · one repair request carries the problem; a good second answer is written and counted."""
    translator = ScriptedTranslator({"documents.count_one": ["документ", prefixed("ru", "{count} Dokument")]})

    report = translate_locale(_job(), translator, files)

    repair = translator.batches[-1]
    assert [unit.key for unit in repair.units] == ["documents.count_one"]
    assert "placeholders" in repair.corrections[0].problems[0]
    assert report.repaired == 1 and report.rejected == ()
    assert _flat(files)["documents.count_one"] == prefixed("ru", "{count} Dokument")


def test_a_string_that_still_fails_after_the_repair_is_reported_and_left_absent(files: TranslationFiles) -> None:
    """translate · one repair, never a third request: the key is reported with its problems and not written."""
    translator = ScriptedTranslator({"documents.count_one": ["документ", "документ", "документ"]})

    report = translate_locale(_job(), translator, files)

    assert translator.asked_keys.count("documents.count_one") == 2
    assert [rejection.key for rejection in report.rejected] == ["documents.count_one"]
    assert "placeholders" in report.rejected[0].problems[0]
    assert "documents.count_one" not in _flat(files)
    assert report.gaps == ["documents.count_one"]


def test_an_untranslated_english_copy_is_repaired_and_then_rejected_when_it_stays(files: TranslationFiles) -> None:
    """translate · English copied back is a finding like any other: repaired once, rejected if it stays."""
    translator = ScriptedTranslator({"common.save": ["Save", "Save"]})

    report = translate_locale(_job("tr", SOURCES[:2]), translator, files)

    assert [r.key for r in report.rejected] == ["common.save"] and "common.save" not in files.read("tr")
    assert "untranslated_english" in report.rejected[0].problems[0]


def test_a_quota_stop_ends_the_run_cleanly_and_writes_nothing_of_the_interrupted_batch(
    files: TranslationFiles,
) -> None:
    """translate · stops cleanly on quota exhaustion and writes nothing partial per batch; a rerun continues."""
    translator = ScriptedTranslator(errors={2: StopDrain("llm_quota", "allowance gone")})

    report = translate_locale(_job("tr", batch_size=2), translator, files)

    assert report.stopped == "llm_quota"
    assert set(files.read("tr")) == {"common.save", "common.cancel"} and report.translated == 2
    assert report.remaining == len(SOURCES) - 2
    resumed = translate_locale(_job("tr", batch_size=2), ScriptedTranslator(), files)
    assert resumed.stopped is None and len(files.read("tr")) == len(SOURCES)


def test_a_batch_the_engine_cannot_answer_is_reported_and_the_run_goes_on(files: TranslationFiles) -> None:
    """translate · an unusable answer fails only its batch: those keys are reported, later batches are written."""
    translator = ScriptedTranslator(errors={1: UnusableOutputError("short answer")})

    report = translate_locale(_job("tr", batch_size=2), translator, files)

    assert {r.key for r in report.rejected} == {"common.save", "common.cancel"}
    assert "short answer" in report.rejected[0].problems[0]
    assert set(files.read("tr")) == {string.key for string in SOURCES[2:]}


def test_a_plural_family_with_a_missing_form_is_listed_as_a_gap(files: TranslationFiles) -> None:
    """translate · Russian needs four forms; a rejected `many` leaves a gap the report names."""
    translator = ScriptedTranslator({"documents.count_many": ["x", "x"]})

    report = translate_locale(_job(), translator, files)

    assert "documents.count_many" in report.gaps


def test_the_files_are_deterministic_sorted_and_stable_across_runs(files: TranslationFiles, tmp_path: Path) -> None:
    """translate · reruns produce the same bytes: sorted keys, two-space indent, one trailing newline."""
    translate_locale(_job(), ScriptedTranslator(), files)
    first = (tmp_path / "seed" / "ru.json").read_text(encoding="utf-8")

    translate_locale(_job(), ScriptedTranslator(), files)

    assert (tmp_path / "seed" / "ru.json").read_text(encoding="utf-8") == first
    keys = list(json.loads(first))
    assert keys == sorted(keys) and first.endswith("}\n") and not first.endswith("\n\n")
