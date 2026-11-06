"""Percent repair of model text before grounding, driven by the recorded answer for aa-ferienbeschaeftigung."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from discovery_ingest.extract.clean import clean_page
from discovery_ingest.extract.llm.evaluation.gold import load_gold
from discovery_ingest.extract.llm.ground import Grounded, ground
from discovery_ingest.extract.llm.schema import PageExtraction
from discovery_ingest.extract.llm.taxonomy import Taxonomy

from crosswalk_fakes import CROSSWALK
from llm_fakes import page

FIXTURES = Path(__file__).parent / "fixtures"
GOLD_DIR = FIXTURES / "gold"
ANSWER = FIXTURES / "llm_answers" / "aa-ferienbeschaeftigung.answer.json"
TEXT = "# Antrag\nBitte reichen Sie die Erklärung zur Immatrikulationsbescheinigung ein. Preis: 100% sicher."
LINK = "https://portal.example/formulare/erkl%C3%A4rung%20alt.pdf"


def _taxonomy() -> Taxonomy:
    return Taxonomy.model_validate_json((GOLD_DIR / "taxonomy.json").read_text(encoding="utf-8"), context=CROSSWALK)


def _ground(documents: list[dict[str, Any]], text: str = TEXT, links: tuple[str, ...] = ()) -> Grounded:
    payload = {"page_kind": "service", "category_codes": [], "documents": documents}
    extraction = PageExtraction.model_validate({**payload, "dependencies": []})
    return ground(extraction, page(text, links=links), _taxonomy())


def _doc(name: str, quote: str, **extra: Any) -> dict[str, Any]:
    return {"name": name, "role": "required", "quote": quote, **extra}


def _recorded_page() -> Any:
    gold = next(item for item in load_gold(GOLD_DIR, crosswalk=CROSSWALK) if item.name == "aa-ferienbeschaeftigung")
    return clean_page(gold.html, gold.source_url)


def test_a_percent_encoded_name_and_quote_are_decoded_and_then_grounded_against_the_cleaned_text() -> None:
    """repair · of six encoded items of the recorded answer, two documents now ground (two more differ in quote marks)."""
    extraction = PageExtraction.model_validate(json.loads(ANSWER.read_text(encoding="utf-8")))

    grounded = ground(extraction, _recorded_page(), _taxonomy())

    names = [item.name for item in grounded.documents]
    assert "Antragsformular Ferienbeschäftigung" in names
    assert "Bestätigung der Ferienbeschäftigung" in names
    assert grounded.diagnostics.repaired == 6


def test_an_encoded_condition_is_decoded_and_the_encoded_item_is_counted_once() -> None:
    """repair · a condition with sequences is repaired in the same item, which counts once however many fields change."""
    quote = "Erkl%C3%A4rung zur Immatrikulationsbescheinigung"
    encoded = _doc("Erkl%C3%A4rung", quote, condition="f%C3%BCr Studierende")

    grounded = _ground([encoded])

    assert [(item.name, item.condition) for item in grounded.documents] == [("Erklärung", "für Studierende")]
    assert grounded.diagnostics.repaired == 1


def test_a_string_with_one_sequence_or_invalid_utf8_is_left_unchanged_and_fails_grounding_when_off_the_page() -> None:
    """repair · one sequence, or bytes that are not UTF-8, are not touched and the quote is still checked."""
    one_sequence = _doc("Erkl%C3rung", "Erkl%C3rung zur Immatrikulationsbescheinigung")
    bad_bytes = _doc("Erkl%C3%28rung", "Erkl%C3%28rung zur Immatrikulationsbescheinigung")

    grounded = _ground([one_sequence, bad_bytes])

    assert grounded.documents == ()
    assert grounded.diagnostics.dropped == {"quote": 2}
    assert grounded.diagnostics.repaired == 0


def test_a_percent_sign_that_is_not_a_sequence_is_not_repaired() -> None:
    """repair · plain text such as 100% on the page keeps its quote and is not counted as repaired."""
    grounded = _ground([_doc("Preisangabe", "Preis: 100% sicher.")])

    assert [item.name for item in grounded.documents] == ["Preisangabe"]
    assert grounded.diagnostics.repaired == 0


def test_urls_are_never_decoded_by_the_repair() -> None:
    """repair · a link that carries percent sequences is matched and kept as written."""
    document = _doc("Erklärungsformular", "Bitte reichen Sie die Erklärung", url=LINK)

    grounded = _ground([document], links=(LINK,))

    assert [item.url for item in grounded.documents] == [LINK]
    assert grounded.diagnostics.repaired == 0


def test_the_repaired_count_is_reported_in_the_diagnostics() -> None:
    """repair · two encoded items and one plain item give a count of two."""
    quote = "Erkl%C3%A4rung zur Immatrikulationsbescheinigung"
    documents = [_doc("Erkl%C3%A4rung", quote), _doc("%C3%9Cbersicht", quote), _doc("Plain", "Preis: 100% sicher.")]

    assert _ground(documents).diagnostics.repaired == 2
