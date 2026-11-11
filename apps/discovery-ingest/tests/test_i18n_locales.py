"""The UI target locales and the English texts that may stay unchanged (search-first C11)."""

from __future__ import annotations

from discovery_ingest.i18n.locales import UI_TARGET_LOCALES, allow_unchanged
from discovery_ingest.i18n.plural import PLURAL_CATEGORIES
from discovery_ingest.translation.locale_codes import DEFAULT_TARGET_LOCALES


def test_the_ui_targets_are_the_document_locales_without_english_and_each_has_plural_forms() -> None:
    """locales · one list of codes: the core's, minus the hand-written English; the plural table covers each."""
    assert UI_TARGET_LOCALES == ("tr", "ru", "uk", "pl", "ro")
    assert set(UI_TARGET_LOCALES) == set(DEFAULT_TARGET_LOCALES) - {"en"} == set(PLURAL_CATEGORIES)


def test_brand_names_may_stay_unchanged_in_every_locale_and_ordinary_words_in_none() -> None:
    """locales · the allow list holds brands and codes, not words."""
    for locale in UI_TARGET_LOCALES:
        allowed = allow_unchanged(locale)
        assert {"GovData", "Redtape"} <= allowed and "Save" not in allowed
