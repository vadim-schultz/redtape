"""UI validators: each is a small pure function; a locale's plural family must be complete (search-first C11)."""

from __future__ import annotations

import pytest
from discovery_ingest.i18n.plural import PLURAL_CATEGORIES
from discovery_ingest.i18n.strings import SourceString
from discovery_ingest.i18n.validate_ui import (
    interface_findings,
    layout_length,
    plural_forms_complete,
    untranslated_copy,
)
from discovery_ingest.translation.findings import Finding
from discovery_ingest.translation.glossary import Glossary
from discovery_ingest.translation.validate import validate_text

from ui_fakes import GLOSSARY, source

COUNT = source("documents.count_other", "{count} documents", "{count} Dokumente")
ALLOW = frozenset({"redtape"})


def validate_string(string: SourceString, translated: str, glossary: Glossary, allow: frozenset[str]) -> list[Finding]:
    """What the flow runs: the core's checks against the German text plus the interface checks against the English."""
    return [*validate_text(string.german, translated, glossary), *interface_findings(string, translated, allow)]


def _checks(translated: str) -> set[str]:
    string = source("documents.count_other", "{count} documents", "{count} Dokumente")
    return {finding.check for finding in validate_string(string, translated, GLOSSARY, ALLOW)}


def test_a_translation_with_identical_placeholders_and_a_complete_plural_family_is_accepted() -> None:
    """validate · accepts a translation with identical placeholders and complete plural forms."""
    keys = [f"documents.count_{category}" for category in PLURAL_CATEGORIES["ru"]]

    assert validate_string(COUNT, "{count} документов", GLOSSARY, ALLOW) == []
    assert plural_forms_complete("ru", keys) == []


@pytest.mark.parametrize(
    ("translated", "check"),
    [
        ("документов", "placeholders"),
        ("{total} документов", "placeholders"),
        ("{count} {count} документов", "placeholders"),
        ("{count} <b>документов</b>", "markup"),
        ("**{count}** документов", "markup"),
        ("", "non_empty"),
    ],
)
def test_a_dropped_renamed_or_added_placeholder_or_added_markup_is_rejected(translated: str, check: str) -> None:
    """validate · rejects a dropped or renamed placeholder, or added markup, naming the broken check."""
    assert check in _checks(translated)


def test_a_plural_family_missing_a_form_the_locale_needs_is_reported_by_key() -> None:
    """validate · rejects a missing plural form: Russian needs few and many, Romanian few."""
    forms = ("documents.count_one", "documents.count_other")

    assert plural_forms_complete("ru", forms) == ["documents.count_few", "documents.count_many"]
    assert plural_forms_complete("ro", forms) == ["documents.count_few"]
    assert plural_forms_complete("tr", forms) == []


def test_a_plain_key_that_ends_in_other_is_not_a_plural_family() -> None:
    """validate · `title` beside `title_other` is two plain keys, as the web parity test treats it."""
    assert plural_forms_complete("ru", ["title", "title_other"]) == []


def test_an_untranslated_copy_of_the_english_source_is_flagged() -> None:
    """validate · flags an untranslated copy of the English source."""
    assert "untranslated_english" in _checks("{count} documents")
    assert "untranslated_english" in _checks("{count} Documents")


def test_an_allow_listed_brand_name_may_stay_as_the_english_source() -> None:
    """validate · a brand name on the allow list, or text without words (a code), is not an untranslated copy."""
    assert untranslated_copy("redtape", ALLOW)("redtape", "redtape") is None
    assert untranslated_copy("{count}", ALLOW)("{count}", "{count}") is None
    assert untranslated_copy("Status", ALLOW)("Status", "Status") is not None


@pytest.mark.parametrize("translated", ["x", "{count} " + "документов " * 12])
def test_a_translation_that_would_break_the_layout_is_flagged(translated: str) -> None:
    """validate · a stub or a runaway against the English length is flagged."""
    assert layout_length("{count} documents")("{count} documents", translated) is not None


def test_a_glossary_term_rendered_differently_in_the_output_is_flagged() -> None:
    """glossary · `Antrag` must come out as `заявление`; another word is a glossary finding."""
    string = source("forms.apply", "Application form", "Antrag stellen")

    assert validate_string(string, "Подать заявление", GLOSSARY, ALLOW) == []
    assert {f.check for f in validate_string(string, "Подать приложение", GLOSSARY, ALLOW)} == {"glossary"}


def test_every_plural_category_list_matches_the_locales_the_core_translates_into() -> None:
    """validate · the plural table covers exactly the UI target locales."""
    assert set(PLURAL_CATEGORIES) == {"tr", "ru", "uk", "pl", "ro"}
    assert PLURAL_CATEGORIES["ru"] == ("one", "few", "many", "other")
    assert PLURAL_CATEGORIES["ro"] == ("one", "few", "other")
