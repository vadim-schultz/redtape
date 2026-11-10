from __future__ import annotations

from app.i18n_resolution import pick_i18n
from app.shared.locale import ResolvedLocale, fallback_chain


def _locale(code: str, *enabled: str) -> ResolvedLocale:
    return ResolvedLocale(code=code, enabled=set(enabled) or {code})


def test_pick_i18n_prefers_requested_then_de_then_en_then_sorted_enabled_then_any() -> None:
    assert pick_i18n({"de": "Wohnen", "en": "Housing"}, _locale("en", "de", "en")) == "Housing"
    assert pick_i18n({"de": "Wohnen", "it": "Casa"}, _locale("en", "de", "en", "it")) == "Wohnen"
    assert pick_i18n({"it": "Casa", "fr": "Logement"}, _locale("en", "de", "en", "fr", "it")) == "Logement"
    assert pick_i18n({"xx": "Something"}, _locale("en", "de", "en")) == "Something"


def test_pick_i18n_skips_blank_values() -> None:
    assert pick_i18n({"de": "Wohnen", "en": "  "}, _locale("en", "de", "en")) == "Wohnen"


def test_pick_i18n_returns_empty_for_none_and_for_all_blank() -> None:
    assert pick_i18n(None, _locale("de")) == ""
    assert pick_i18n({"de": "  ", "en": ""}, _locale("de", "de", "en")) == ""


def test_pick_i18n_honours_explicit_fallback_order() -> None:
    values = {"en": "Housing", "de": "Wohnen"}
    assert pick_i18n(values, ResolvedLocale(code="fr", enabled={"fr"}), fallback=("en", "de")) == "Housing"


def test_fallback_chain_puts_en_before_de_for_non_german_readers() -> None:
    assert fallback_chain("tr") == ("tr", "en", "de")
    assert fallback_chain("en") == ("en", "de")
    assert fallback_chain("ro") == ("ro", "en", "de")


def test_fallback_chain_keeps_de_before_en_for_german_readers() -> None:
    assert fallback_chain("de") == ("de", "en")


def test_a_turkish_reader_gets_en_before_de() -> None:
    turkish = _locale("tr", "de", "en", "tr")

    assert pick_i18n({"de": "Wohnen", "en": "Housing"}, turkish) == "Housing"
    assert pick_i18n({"de": "Wohnen"}, turkish) == "Wohnen"
    assert pick_i18n({"tr": "Konut", "en": "Housing", "de": "Wohnen"}, turkish) == "Konut"


def test_german_readers_still_get_de_before_en() -> None:
    assert pick_i18n({"de": "Wohnen", "en": "Housing"}, _locale("de", "de", "en")) == "Wohnen"
    assert pick_i18n({"en": "Housing"}, _locale("de", "de", "en")) == "Housing"


def test_an_unlisted_reader_falls_through_en_then_de_then_enabled() -> None:
    assert pick_i18n({"de": "Wohnen", "en": "Housing"}, _locale("fr", "fr")) == "Housing"
    assert pick_i18n({"it": "Casa"}, _locale("fr", "it")) == "Casa"
