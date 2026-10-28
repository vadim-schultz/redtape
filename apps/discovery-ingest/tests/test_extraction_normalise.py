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
