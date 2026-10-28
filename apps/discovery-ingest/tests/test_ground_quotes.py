"""Quote grounding folds list bullets and quote glyphs the same way on the quote and on the page."""

from __future__ import annotations

from typing import Any

from discovery_ingest.extract.llm.ground import Grounded, ground
from discovery_ingest.extract.llm.schema import PageExtraction

from llm_fakes import page, taxonomy

TEXT = """# Probebeschäftigung
Sie benötigen:
- Kundennummer der Person
- Schwerbehindertenausweis
Alle Unterlagen: - Meldebescheinigung - Geburtsurkunde
Das Formular „Antrag auf Leistung“ liegt bei.
Die Bundes-Agentur – kurz BA – hilft."""


def run(quote: str, text: str = TEXT) -> Grounded:
    document: dict[str, Any] = {"name": "Dokument", "role": "required", "quote": quote}
    payload = {"page_kind": "service", "domain_codes": [], "situation_codes": [], "documents": [document]}
    return ground(PageExtraction.model_validate({**payload, "dependencies": []}), page(text), taxonomy())


def test_a_quote_spanning_a_heading_and_a_bullet_grounds_against_text_with_them_on_separate_lines() -> None:
    """bullets · the model joined the heading line and its first bullet with ``- ``."""
    assert len(run("Sie benötigen: - Kundennummer der Person").documents) == 1


def test_a_bullet_inside_a_line_of_the_page_text_is_removed_the_same_way() -> None:
    """bullets · the page itself has ``- `` between two items on one line, the quote has none."""
    assert len(run("Alle Unterlagen: Meldebescheinigung Geburtsurkunde").documents) == 1


def test_a_quote_whose_words_are_not_on_the_page_still_fails_with_bullets() -> None:
    """bullets · a bullet does not make an invented line grounded (negative)."""
    grounded = run("Sie benötigen: - Reisepass der Person")
    assert grounded.documents == ()
    assert grounded.diagnostics.dropped == {"quote": 1}
