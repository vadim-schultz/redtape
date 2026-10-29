"""The generic-name guard: devices, apps, generic words, leaflets and lists of authorities are not documents."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from discovery_ingest.extract.llm.generic_names import GENERIC_NAME_PATTERNS, is_generic_name

from test_extraction_grounding import doc, names, run

GOLD = Path(__file__).parent / "fixtures" / "gold"
SEEN_ON_THE_EVAL_PAGES = (
    "PDF-Formular",
    "Online-Formular",
    "Antragsformularen",
    "Bestätigung",
    "Bekanntmachung",
    "Sonstige",
    "Behördenliste - Hangnachweis",
    "Datenschutzhinweise",
    "Informationen zum Datenschutz",
    "Merkblatt 8c - Transferleistungen",
    "Informationen und Ausfüllhinweise für die Beantragung einer Neuanpflanzung von Weinreben",
    "Hinweise zum Antragsverfahren bei Kurzarbeitergeld",
    "Kartenlesegerät",
    "Smartphone",
    "AusweisApp2",
    "digitales Erfassungsgerät",
    "Filmwerke",
    "Schriftwerke",
    "Spiele",
)
SPECIFIC_NAMES = (
    "Antragsformular Grundstückskauf",
    "Bestätigung der Ferienbeschäftigung",
    "Online-Meldeformular",
    "Onlineantrag",
    "Antrag auf Indizierung",
    "Nachweis des Verwandtschaftsverhältnisses",
    "Formular Antrag Transferkurzarbeitergeld",
    "Genehmigungsbescheide",
    "Knapp",
    "Datenblatt Lesegerät-Zulassung",
)


def _gold_names() -> list[str]:
    files = sorted(GOLD.glob("*.gold.json"))
    return [d["name"] for f in files for d in json.loads(f.read_text(encoding="utf-8")).get("documents", [])]


@pytest.mark.parametrize("name", SEEN_ON_THE_EVAL_PAGES)
def test_a_name_that_is_a_generic_word_or_a_non_document_kind_is_generic(name: str) -> None:
    """guard · the names the models returned on the 2026-10-29 eval pages match."""
    assert is_generic_name(name)


@pytest.mark.parametrize("name", SPECIFIC_NAMES)
def test_a_specific_name_that_contains_a_generic_word_is_not_generic(name: str) -> None:
    """guard · negative: the patterns match a whole generic name or its start, not a word inside a specific name."""
    assert not is_generic_name(name)


def test_a_generic_name_is_dropped_with_the_reason_generic_name_and_a_specific_name_is_kept() -> None:
    """guard · grounding drops the generic name, keeps the specific one and keeps the dropped item for review."""
    grounded = run([doc("Bestätigung"), doc("Antragsformular Grundstückskauf"), doc("Behördenliste - Wein")])
    assert names(grounded) == ["Antragsformular Grundstückskauf"]
    assert [(d.reason, d.item.name) for d in grounded.diagnostics.dropped_items] == [
        ("generic_name", "Bestätigung"),
        ("generic_name", "Behördenliste - Wein"),
    ]


def test_a_noise_name_keeps_its_own_reason_before_the_generic_check() -> None:
    """guard · negative: the reasons keep their order (noise, data_field, generic_name, duplicate)."""
    grounded = run([doc("Kundennummer der Person"), doc("Formular"), doc("Personalausweis"), doc("Personalausweis")])
    assert grounded.diagnostics.dropped == {"data_field": 1, "generic_name": 1, "duplicate": 1}


def test_no_gold_document_name_on_the_committed_gold_set_is_dropped_by_the_guard() -> None:
    """guard · negative, over every gold name (47 at the time of writing)."""
    gold = _gold_names()
    assert len(gold) >= 47
    assert [name for name in gold if is_generic_name(name)] == []


def test_the_patterns_are_a_named_tuple_of_compiled_expressions() -> None:
    """guard · a tuple of patterns, not a model call."""
    assert isinstance(GENERIC_NAME_PATTERNS, tuple)
    assert GENERIC_NAME_PATTERNS
    assert all(hasattr(pattern, "search") for pattern in GENERIC_NAME_PATTERNS)


def test_diagnostics_counts_the_dropped_generic_names() -> None:
    """guard · the drop count per reason carries ``generic_name``."""
    grounded = run([doc("PDF-Formular"), doc("Smartphone"), doc("Personalausweis")])
    assert grounded.diagnostics.dropped == {"generic_name": 2}


def test_diagnostics_has_no_generic_name_entry_when_nothing_was_dropped() -> None:
    """guard · negative: the reason is left out when it never occurred."""
    assert "generic_name" not in run([doc("Personalausweis")]).diagnostics.dropped
