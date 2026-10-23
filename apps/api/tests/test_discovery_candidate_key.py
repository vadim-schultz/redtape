"""Candidate key equals the promotion slug rule (chapter 6, loop A)."""

from __future__ import annotations

import pytest
from app.features.discovery.candidate_key import candidate_key
from app.features.discovery.errors import InvalidDiscoveryInputError
from app.features.suggestions.slugs import pick_title, slugify

TITLES: list[dict[str, str]] = [
    {"de": "Führungszeugnis"},
    {"de": "Geburtsurkunde (beglaubigt)", "en": "Birth certificate"},
    {"de": "Antrag auf Wohngeld – Formular 1/2"},
    {"fr": "Passeport"},
    {"de": "  ", "fr": "Carte d'identité"},
    {"de": "Personalausweis / Reisepass"},
]


@pytest.mark.parametrize("title_i18n", TITLES)
def test_candidate_key_matches_the_promotion_slug_for_the_same_title(title_i18n: dict[str, str]) -> None:
    assert candidate_key(title_i18n) == slugify(pick_title(title_i18n))


def test_candidate_key_rejects_a_title_with_no_usable_characters() -> None:
    with pytest.raises(InvalidDiscoveryInputError):
        candidate_key({"de": "!!! ???"})


def test_candidate_key_rejects_an_empty_title() -> None:
    with pytest.raises(InvalidDiscoveryInputError):
        candidate_key({"de": "   "})


def test_candidate_key_is_stable_across_whitespace_and_case() -> None:
    assert candidate_key({"de": "  PERSONALAUSWEIS "}) == candidate_key({"de": "Personalausweis"})
