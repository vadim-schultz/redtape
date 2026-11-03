from __future__ import annotations

from app.i18n_resolution import pick_i18n
from app.shared.locale import ResolvedLocale


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
