"""Query normalisation: Unicode, whitespace, length and locale-aware lower-casing (chapter 8)."""

from __future__ import annotations

import pytest
from app.features.search.query import NormalisedQuery, normalise_query
from app.shared.list_query import SEARCH_MAX_LENGTH


def test_normalisation_composes_trims_and_collapses_whitespace() -> None:
    decomposed = "  Kündigung \t der\n Wohnung  "

    assert normalise_query(decomposed, "de") == NormalisedQuery("kündigung der wohnung", "de")


def test_normalisation_lower_cases_in_application_code() -> None:
    assert normalise_query("KINDERGELD Antrag", "en") == NormalisedQuery("kindergeld antrag", "en")


def test_turkish_dotted_and_dotless_i_are_lower_cased_correctly() -> None:
    assert normalise_query("ISPARTA İSTANBUL", "tr").text == "ısparta istanbul"


def test_other_locales_lower_case_i_to_plain_i_and_keep_no_combining_dot() -> None:
    assert normalise_query("ISPARTA", "de").text == "isparta"
    assert normalise_query("İSTANBUL", "de").text == "istanbul"


def test_an_overlong_query_is_cut_to_the_length_cap_on_a_word_boundary() -> None:
    long = " ".join(["antrag"] * 80)

    result = normalise_query(long, "de")

    assert result is not None
    assert len(result.text) <= SEARCH_MAX_LENGTH
    assert result.text.endswith("antrag")


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_a_blank_query_is_no_query(blank: str) -> None:
    assert normalise_query(blank, "de") is None
