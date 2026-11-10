"""The one SUPPORTED_LOCALES list and the locale-key validator built on it."""

from __future__ import annotations

import pytest
from app.schema.locale.keys import validate_locale_key, validate_locale_keys
from app.shared.locale import DEFAULT_ENABLED_LOCALES, SUPPORTED_LOCALES

EXPECTED_CODES = ("de", "en", "tr", "ru", "uk", "pl", "ro")


def test_supported_locales_lists_the_seven_codes_with_names_and_flags() -> None:
    assert tuple(spec.code for spec in SUPPORTED_LOCALES) == EXPECTED_CODES
    assert all(spec.name_native and spec.name_english and spec.flag_emoji for spec in SUPPORTED_LOCALES)


def test_only_de_and_en_are_enabled_by_default() -> None:
    assert frozenset({"de", "en"}) == DEFAULT_ENABLED_LOCALES


@pytest.mark.parametrize("code", EXPECTED_CODES)
def test_validate_locale_key_accepts_supported_codes_case_insensitively(code: str) -> None:
    assert validate_locale_key(code.upper()) == code


@pytest.mark.parametrize("key", ["fr", "xx", "", "deu", "de-AT", " de"])
def test_validate_locale_key_rejects_others_naming_the_key(key: str) -> None:
    with pytest.raises(ValueError, match=f"unsupported locale code: {key!r}"):
        validate_locale_key(key)


def test_validate_locale_keys_lowercases_keys_and_keeps_values() -> None:
    assert validate_locale_keys({"DE": "Wohnen", "en": "Housing"}) == {"de": "Wohnen", "en": "Housing"}


def test_validate_locale_keys_rejects_the_first_unsupported_key() -> None:
    with pytest.raises(ValueError, match="unsupported locale code: 'fr'"):
        validate_locale_keys({"de": "Wohnen", "fr": "Logement"})
