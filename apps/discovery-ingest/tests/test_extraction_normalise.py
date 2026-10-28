"""Slug and quote normalisation rules shared by grounding and mapping."""

from __future__ import annotations

import pytest
from discovery_ingest.extract.llm.normalise import name_slug, normalise


@pytest.mark.parametrize(
    ("name", "slug"),
    [
        ("Personalausweis", "personalausweis"),
        ("Bescheinigung über den Wohnsitz", "bescheinigung-uber-den-wohnsitz"),
        ("Geburtsurkunde (beglaubigt)", "geburtsurkunde-beglaubigt"),
        ("  Meldebescheinigung  ", "meldebescheinigung"),
        ("Личное дело", ""),
    ],
)
def test_the_slug_follows_the_promotion_rule(name: str, slug: str) -> None:
    assert name_slug(name) == slug


def test_normalise_drops_markers_bullets_and_link_targets() -> None:
    assert normalise("- **Antrag**  [Formular](https://a.example/x)\n| Zeile") == "antrag formular zeile"


def test_normalise_keeps_hyphens_inside_words() -> None:
    assert normalise("E-Mail-Adresse") == "e-mail-adresse"


def test_a_bullet_in_the_middle_of_a_line_is_removed_like_one_at_its_start() -> None:
    """bullets · a heading and a bullet on one line fold to the same text as on two lines."""
    assert normalise("Sie benötigen: - Pass") == normalise("Sie benötigen:\n- Pass") == "sie benötigen: pass"


def test_every_bullet_glyph_after_whitespace_is_removed_wherever_it_stands() -> None:
    """bullets · hyphen, plus, dot glyphs and a star are list markers when a space follows them."""
    assert normalise("Pass • Ausweis · Foto + Antrag * Kopie - Urkunde") == "pass ausweis foto antrag kopie urkunde"


def test_a_hyphen_inside_a_word_or_a_number_is_not_a_bullet() -> None:
    """bullets · only a marker after whitespace and before a space is removed (negative)."""
    assert (
        normalise("Bundes-Agentur und Bundes- sowie -5 Grad, E-Mail")
        == "bundes-agentur und bundes- sowie -5 grad, e-mail"
    )
