"""Plural expansion: `key_one` and `key_other` of the source become the target locale's plural forms (search-first C11)."""

from __future__ import annotations

import pytest
from discovery_ingest.i18n.plural import expand_plurals

from ui_fakes import source

STRINGS = [
    source("documents.count_one", "{count} document", "{count} Dokument"),
    source("documents.count_other", "{count} documents", "{count} Dokumente"),
    source("suggest.title_other", "Suggestions", "Vorschläge"),
    source("common.save", "Save", "Speichern"),
]


def _by_key(locale: str) -> dict[str, str]:
    return {string.key: string.german for string in expand_plurals(STRINGS, locale)}


@pytest.mark.parametrize(
    ("locale", "forms"),
    [
        ("ru", ["one", "few", "many", "other"]),
        ("pl", ["one", "few", "many", "other"]),
        ("uk", ["one", "few", "many", "other"]),
        ("ro", ["one", "few", "other"]),
        ("tr", ["one", "other"]),
    ],
)
def test_one_and_other_source_keys_expand_into_the_target_locales_plural_categories(
    locale: str, forms: list[str]
) -> None:
    """translate · expands one/other source keys into the target locale's plural categories."""
    keys = _by_key(locale)

    assert [key for key in keys if key.startswith("documents.count_")] == [f"documents.count_{form}" for form in forms]
    assert keys["documents.count_one"] == "{count} Dokument"
    assert all(keys[f"documents.count_{form}"] == "{count} Dokumente" for form in forms if form != "one")


def test_a_family_with_only_an_other_form_expands_from_that_form_and_plain_keys_pass_through() -> None:
    """translate · `suggest.title_other` alone still needs every category; `common.save` is untouched."""
    keys = _by_key("ru")

    assert [k for k in keys if k.startswith("suggest.")] == [
        f"suggest.title_{f}" for f in ("one", "few", "many", "other")
    ]
    assert keys["common.save"] == "Speichern"


def test_an_expanded_form_tells_the_model_its_category_and_example_counts() -> None:
    """translate · the note of `count_few` names the category and the counts that use it, so the model inflects."""
    few = next(s for s in expand_plurals(STRINGS, "ru") if s.key == "documents.count_few")

    assert "few" in few.note and "2" in few.note
    assert few.english == "{count} documents"


def test_a_locale_without_a_plural_table_is_refused() -> None:
    """translate · an unknown locale raises instead of guessing its plural forms."""
    with pytest.raises(KeyError, match="fr"):
        expand_plurals(STRINGS, "fr")
