from __future__ import annotations

import pytest
from app.locale_resolution import normalize_locale_tag, resolve_locale


def test_query_locale_wins_over_accept_language() -> None:
    assert resolve_locale(query_locale="en", accept_language="de;q=1.0", enabled={"de", "en"}) == "en"


def test_accept_language_picks_highest_q_among_enabled() -> None:
    header = "fr;q=0.9, en;q=0.8, de;q=0.5"
    assert resolve_locale(query_locale=None, accept_language=header, enabled={"de", "en"}) == "en"


def test_unknown_tag_falls_back_de_then_en_then_first_enabled() -> None:
    assert resolve_locale(query_locale="xx", accept_language=None, enabled={"fr"}) == "fr"


def test_empty_enabled_set_means_de_en() -> None:
    assert resolve_locale(query_locale=None, accept_language=None, enabled=set()) == "de"


ALL_CODES = ["de", "en", "tr", "ru", "uk", "pl", "ro"]


@pytest.mark.parametrize("code", ["tr", "ru", "uk", "pl", "ro"])
def test_new_locales_resolve_by_query_and_accept_language_when_enabled(code: str) -> None:
    enabled = set(ALL_CODES)

    assert resolve_locale(query_locale=code, accept_language=None, enabled=enabled) == code
    assert resolve_locale(query_locale=None, accept_language=f"{code};q=0.9, en;q=0.5", enabled=enabled) == code


@pytest.mark.parametrize(("tag", "expected"), [("de-AT", "de"), ("tr-TR", "tr"), ("pt-BR", "pt"), ("uk-UA", "uk")])
def test_region_subtags_resolve_to_the_primary_code(tag: str, expected: str) -> None:
    assert normalize_locale_tag(tag) == expected
    assert resolve_locale(query_locale=tag, accept_language=None, enabled=set(ALL_CODES)) in {expected, "de"}
    assert resolve_locale(query_locale="de-AT", accept_language=None, enabled={"de", "en"}) == "de"


@pytest.mark.parametrize("code", ["tr", "ru", "uk", "pl", "ro"])
def test_a_disabled_locale_is_never_served(code: str) -> None:
    enabled = {"de", "en"}

    assert resolve_locale(query_locale=code, accept_language=None, enabled=enabled) == "de"
    assert resolve_locale(query_locale=None, accept_language=f"{code}-XX,{code};q=0.9", enabled=enabled) == "de"
