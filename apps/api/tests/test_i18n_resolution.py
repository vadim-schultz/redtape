from __future__ import annotations

from app.i18n_resolution import pick_i18n


def test_requested_locale_wins() -> None:
    assert pick_i18n({"de": "Wohnen", "en": "Housing"}, locale="en", enabled={"de", "en"}) == "Housing"


def test_falls_back_to_de_when_locale_missing() -> None:
    assert pick_i18n({"de": "Wohnen"}, locale="en", enabled={"de", "en"}) == "Wohnen"


def test_blank_values_are_skipped() -> None:
    assert pick_i18n({"de": "Wohnen", "en": "  "}, locale="en", enabled={"de", "en"}) == "Wohnen"


def test_empty_map_resolves_to_empty_string() -> None:
    assert pick_i18n(None, locale="de", enabled={"de"}) == ""
