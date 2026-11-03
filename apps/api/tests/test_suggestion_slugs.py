from __future__ import annotations

import pytest
from app.features.suggestions.slugs import pick_title, slugify


def test_slugify_folds_umlauts_and_punctuation() -> None:
    assert slugify("Anmeldung für Bürger") == "anmeldung-fur-burger"


def test_pick_title_prefers_english_then_german() -> None:
    assert pick_title({"de": "Anmeldung", "en": "Registration"}) == "Registration"
    assert pick_title({"de": "Anmeldung", "fr": "Inscription"}) == "Anmeldung"
    assert pick_title({"fr": "Inscription"}) == "Inscription"


def test_pick_title_strips_and_skips_blank_en() -> None:
    assert pick_title({"en": "  Registration  ", "de": "Anmeldung"}) == "Registration"
    assert pick_title({"en": "   ", "de": "Anmeldung"}) == "Anmeldung"


def test_pick_title_ignores_requested_locale_order() -> None:
    assert pick_title({"en": " ", "de": "Anmeldung"}) == "Anmeldung"


def test_slugify_raises_on_title_with_no_usable_characters() -> None:
    with pytest.raises(ValueError):
        slugify("!!!")
