from __future__ import annotations

from app.locale_resolution import resolve_locale


def test_query_locale_wins_over_accept_language() -> None:
    assert resolve_locale(query_locale="en", accept_language="de;q=1.0", enabled={"de", "en"}) == "en"


def test_accept_language_picks_highest_q_among_enabled() -> None:
    header = "fr;q=0.9, en;q=0.8, de;q=0.5"
    assert resolve_locale(query_locale=None, accept_language=header, enabled={"de", "en"}) == "en"


def test_unknown_tag_falls_back_de_then_en_then_first_enabled() -> None:
    assert resolve_locale(query_locale="xx", accept_language=None, enabled={"fr"}) == "fr"


def test_empty_enabled_set_means_de_en() -> None:
    assert resolve_locale(query_locale=None, accept_language=None, enabled=set()) == "de"
