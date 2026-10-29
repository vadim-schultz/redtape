"""The data-field guard: names of identifiers, addresses and numbers are not documents."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from discovery_ingest.extract.llm.data_fields import DATA_FIELD_PATTERNS, is_data_field

from test_extraction_grounding import doc, names, run

GOLD = Path(__file__).parent / "fixtures" / "gold"
SEEN_ON_THE_FIRST_PAGES = (
    "Anschrift des personenabgebenden Betriebs",
    "Name und Betriebsnummer des personenabgebenden Betriebs",
    "Betriebsnummer der Lohnabrechnungsstelle der Transfergesellschaft",
    "Transferkurzarbeitergeld-Nummer (TKUG-Nummer)",
    "Kundennummer der Person",
    "Bearbeitungsnummer",
)


def _gold_names() -> list[str]:
    files = sorted(GOLD.glob("*.gold.json"))
    return [d["name"] for f in files for d in json.loads(f.read_text(encoding="utf-8")).get("documents", [])]


@pytest.mark.parametrize("name", SEEN_ON_THE_FIRST_PAGES)
def test_a_name_that_is_an_identifier_or_address_is_a_data_field(name: str) -> None:
    """guard · the names the models returned for ``aa-transferkurzarbeitergeld`` and two other pages match."""
    assert is_data_field(name)


def test_a_name_that_is_an_identifier_or_address_is_dropped_with_the_reason_data_field() -> None:
    """guard · grounding drops it, keeps the document next to it and keeps the dropped item for review."""
    grounded = run([doc("Anschrift des personenabgebenden Betriebs"), doc("Personalausweis")])
    assert names(grounded) == ["Personalausweis"]
    assert [(d.reason, d.item.name) for d in grounded.diagnostics.dropped_items] == [
        ("data_field", "Anschrift des personenabgebenden Betriebs")
    ]


def test_a_document_that_only_mentions_a_number_or_address_is_kept() -> None:
    """guard · negative: the patterns look at the start of the name, not at any word inside it."""
    kept = ("Bescheinigung mit Steuernummer", "Nachweis der Anschrift", "Meldebescheinigung", "Nummernschild")
    assert not any(is_data_field(name) for name in kept)
    assert names(run([doc(name) for name in kept])) == list(kept)


def test_no_gold_document_name_on_the_committed_gold_set_is_dropped_by_the_guard() -> None:
    """guard · negative, over every gold name (47 at the time of writing)."""
    gold = _gold_names()
    assert len(gold) >= 47
    assert [name for name in gold if is_data_field(name)] == []


def test_the_patterns_are_a_named_tuple_of_compiled_expressions() -> None:
    """guard · a tuple of patterns, not a model call."""
    assert isinstance(DATA_FIELD_PATTERNS, tuple)
    assert DATA_FIELD_PATTERNS
    assert all(hasattr(pattern, "search") for pattern in DATA_FIELD_PATTERNS)


def test_diagnostics_counts_the_dropped_data_fields() -> None:
    """guard · the drop count per reason carries ``data_field``."""
    grounded = run([doc("Kundennummer der Person"), doc("Bearbeitungsnummer"), doc("Personalausweis")])
    assert grounded.diagnostics.dropped == {"data_field": 2}


def test_diagnostics_has_no_data_field_entry_when_nothing_was_dropped() -> None:
    """guard · negative: the reason is left out when it never occurred."""
    assert "data_field" not in run([doc("Personalausweis")]).diagnostics.dropped
