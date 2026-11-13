"""The committed locale files and review manifest, held to the same validators as a generated run (search-first C11)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from pathlib import Path

import pytest
from discovery_ingest.i18n.files import Layout, read_flat
from discovery_ingest.i18n.locales import UI_TARGET_LOCALES, allow_unchanged
from discovery_ingest.i18n.manifest import ReviewManifest, load_manifest
from discovery_ingest.i18n.plural import PLURAL_SUFFIX, categories_of, expand_plurals
from discovery_ingest.i18n.strings import SourceString, ui_strings
from discovery_ingest.i18n.validate_ui import (
    indistinct_slavic_families,
    interface_findings,
    plural_forms_complete,
)
from discovery_ingest.translation.glossary import load_glossary
from discovery_ingest.translation.validate import validate_text
from pydantic import ValidationError

LAYOUT = Layout.under(Path(__file__).resolve().parents[3])
SLAVIC = ("ru", "uk", "pl")
HAND_AUTHORED = ("tr", "uk", "pl", "ro")


def _sources() -> list[SourceString]:
    return ui_strings(read_flat(LAYOUT.seed_dir / "en.json"), read_flat(LAYOUT.seed_dir / "de.json"))


def _key_problems(locale: str, required: list[SourceString], flat: Mapping[str, str]) -> list[str]:
    """Return a line for each key ``flat`` lacks or does not need, and for each plural form ``locale`` still needs."""
    keys = {string.key for string in required}
    missing = [f"missing {key}" for key in sorted(keys - set(flat))]
    extra = [f"extra {key}" for key in sorted(set(flat) - keys)]
    gaps = [f"plural gap {key}" for key in plural_forms_complete(locale, flat)]
    return [*missing, *extra, *gaps]


def _text_problems(locale: str, string: SourceString, text: str) -> list[str]:
    """Return a line for each validator finding of ``text``, the translation of ``string``."""
    findings = [
        *validate_text(string.german, text, load_glossary(locale)),
        *interface_findings(string, text, allow_unchanged(locale)),
    ]
    return [f"{string.key}: {finding.check}: {finding.detail}" for finding in findings]


def _problems(locale: str, flat: Mapping[str, str]) -> list[str]:
    """Every missing, extra, plural-gap and validator problem of ``flat`` as one line each."""
    required = expand_plurals(_sources(), locale)
    texts = [_text_problems(locale, string, flat[string.key]) for string in required if string.key in flat]
    return [*_key_problems(locale, required, flat), *(line for lines in texts for line in lines)]


@pytest.mark.parametrize("locale", UI_TARGET_LOCALES)
def test_a_committed_locale_file_is_complete_and_passes_every_interface_validator(locale: str) -> None:
    """committed · every key and plural form is there and no string has a validator finding."""
    flat = read_flat(LAYOUT.seed_dir / f"{locale}.json")

    assert _problems(locale, flat) == []


def test_a_locale_file_losing_a_plural_form_a_placeholder_and_a_key_is_reported() -> None:
    """committed · the check names a missing plural form, a dropped placeholder and a missing key."""
    flat = read_flat(LAYOUT.seed_dir / "ru.json")
    del flat["documents.result_count_few"], flat["common.save"]
    flat["documents.count_many"] = "документов"

    problems = _problems("ru", flat)

    assert "plural gap documents.result_count_few" in problems
    assert "missing common.save" in problems
    assert any(p.startswith("documents.count_many: placeholders") for p in problems)


@pytest.mark.parametrize("locale", UI_TARGET_LOCALES)
def test_every_committed_locale_mirrors_into_the_web_bundle_byte_for_byte(locale: str) -> None:
    """committed · the web mirror equals the API seed file."""
    assert (LAYOUT.mirror_dir / f"{locale}.json").read_bytes() == (LAYOUT.seed_dir / f"{locale}.json").read_bytes()


@pytest.mark.parametrize("locale", SLAVIC)
def test_few_and_many_forms_of_a_slavic_family_are_inflected_differently(locale: str) -> None:
    """committed · no ru, uk or pl family repeats one form for both few and many (the nominative-everywhere defect)."""
    assert indistinct_slavic_families(read_flat(LAYOUT.seed_dir / f"{locale}.json")) == []


def test_a_family_that_repeats_one_form_for_few_and_many_is_found() -> None:
    """committed · the old Russian result_count (few and many both `результаты`) is flagged."""
    flat = {"n_one": "{count} результат", "n_few": "{count} результаты", "n_many": "{count} результаты"}
    flat |= {"n_other": "{count} результаты", "m_few": "a", "m_many": "b", "m_other": "c", "m_one": "d"}

    assert indistinct_slavic_families(flat) == ["n"]


AGREEMENT = {
    "ru": {
        "documents.result_count": ("результат", "результата", "результатов", "результата"),
        "documents.count": ("документ", "документа", "документов", "документа"),
        "suggestions.count": ("предложение", "предложения", "предложений", "предложения"),
        "discovery_admin.tasks.count": ("задача", "задачи", "задач", "задачи"),
    },
    "uk": {
        "documents.result_count": ("результат", "результати", "результатів", "результату"),
        "documents.count": ("документ", "документи", "документів", "документа"),
        "suggestions.count": ("пропозиція", "пропозиції", "пропозицій", "пропозиції"),
        "discovery_admin.tasks.count": ("завдання", "завдання", "завдань", "завдання"),
    },
    "pl": {
        "documents.result_count": ("wynik", "wyniki", "wyników", "wyniku"),
        "documents.count": ("dokument", "dokumenty", "dokumentów", "dokumentu"),
        "suggestions.count": ("propozycja", "propozycje", "propozycji", "propozycji"),
        "discovery_admin.tasks.count": ("zadanie", "zadania", "zadań", "zadania"),
    },
}
"""The counted noun in one, few, many, other: the form after 1, after 2 to 4, after 5 and more, after a fraction."""


@pytest.mark.parametrize(("locale", "family"), [(loc, fam) for loc, fams in AGREEMENT.items() for fam in fams])
def test_the_slavic_plural_forms_agree_with_the_counted_noun(locale: str, family: str) -> None:
    """committed · each pinned family reads `{count} <noun in the case the count takes>` in all four categories."""
    flat = read_flat(LAYOUT.seed_dir / f"{locale}.json")
    forms = AGREEMENT[locale][family]

    found = tuple(flat[f"{family}_{category}"] for category in categories_of(locale))

    assert found == tuple(f"{{count}} {noun}" for noun in forms)


@pytest.mark.parametrize("locale", UI_TARGET_LOCALES)
def test_every_plural_key_of_a_committed_file_ends_in_a_category_of_its_locale(locale: str) -> None:
    """committed · no file carries a plural form its locale never selects (Romanian has no `many`, Turkish no `few`)."""
    suffixes = (PLURAL_SUFFIX.search(key) for key in read_flat(LAYOUT.seed_dir / f"{locale}.json"))

    assert {m.group(1) for m in suffixes if m} <= set(categories_of(locale))


def test_the_committed_manifest_marks_every_locale_machine_and_unreviewed_with_honest_provenance() -> None:
    """committed · every locale is machine text the operator accepted by name and date, none reviewed by a native speaker; the hand-authored four name the model and a manual command version."""
    entries = load_manifest(LAYOUT.seed_dir / "review.json").locales
    accepted = {locale: e for locale, e in entries.items() if e.status == "machine_accepted"}

    assert set(entries) == set(UI_TARGET_LOCALES)
    assert all(e.status in {"machine", "machine_accepted"} for e in entries.values())
    assert all(e.accepted_by == "porcorosso" and e.accepted_on == date(2026, 11, 13) for e in accepted.values())
    assert set(accepted) == set(UI_TARGET_LOCALES), "the operator accepted every target locale"
    assert all(e.reviewed_by is None and e.reviewed_on is None for e in entries.values())
    for locale in HAND_AUTHORED:
        assert entries[locale].model == "claude-sonnet-5-5"
        assert entries[locale].command_version.startswith("claude-code-manual-")
    assert entries["ru"].command_version == "1"


ENGINE_OR_MODEL_NAMES = (
    "azure-translator",
    "llm",
    "claude",
    "claude-sonnet-5-5",
    "qwen3-30b-a3b-fp8",
    "@cf/qwen/qwen3-30b-a3b-fp8",
)


@pytest.mark.parametrize("name", ENGINE_OR_MODEL_NAMES)
def test_an_engine_or_model_named_as_the_accepting_person_fails_the_honesty_check(name: str) -> None:
    """committed · a tool is never the reviewer: accepted_by naming an engine or a model is refused when the manifest loads."""
    entry = {
        "status": "machine_accepted",
        "accepted_by": name,
        "accepted_on": "2026-12-03",
        "model": "claude-sonnet-5-5",
        "command_version": "claude-code-manual-1",
    }

    with pytest.raises(ValidationError, match="must name a person"):
        ReviewManifest.model_validate({"locales": {"tr": entry}})
