"""Grounding of the first live eval's recorded model answers: normalisation recovers glyphs, never inventions."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from discovery_ingest.extract.clean import CleanPage, clean_page
from discovery_ingest.extract.llm.evaluation.drop_reasons import reason_class
from discovery_ingest.extract.llm.evaluation.gold import load_gold
from discovery_ingest.extract.llm.ground import Grounded, ground
from discovery_ingest.extract.llm.ground_names import NAME_REJECTIONS
from discovery_ingest.extract.llm.schema import PageExtraction
from discovery_ingest.extract.llm.taxonomy import Taxonomy

FIXTURES = Path(__file__).parent / "fixtures"
GOLD_DIR = FIXTURES / "gold"
ANSWERS = FIXTURES / "llm_answers"
# Items kept (documents plus dependencies) before this chapter, measured offline on the same answers with E12's grounding.
KEPT_BEFORE = {
    "aa-ferienbeschaeftigung": 5,
    "aa-probebeschaeftigung": 1,
    "aa-transferkurzarbeitergeld": 0,
    "bundesarchiv-akteneinsicht": 5,
}
KEPT_AFTER = {
    "aa-ferienbeschaeftigung": 7,
    "aa-probebeschaeftigung": 2,
    "aa-transferkurzarbeitergeld": 2,
    "bundesarchiv-akteneinsicht": 5,
}
MIN_GAIN = 5


def _extraction(name: str) -> PageExtraction:
    return PageExtraction.model_validate(json.loads((ANSWERS / f"{name}.answer.json").read_text(encoding="utf-8")))


def _page(name: str) -> CleanPage:
    """Return the page as the model read it: ``sr-only`` renamed, so clean-4 does not drop the helper text it copied."""
    gold = next(item for item in load_gold(GOLD_DIR) if item.name == name)
    return clean_page(gold.html.replace("sr-only", "sr-label"), gold.source_url)


def _ground(name: str, extraction: PageExtraction | None = None) -> Grounded:
    taxonomy = Taxonomy.model_validate_json((GOLD_DIR / "taxonomy.json").read_text(encoding="utf-8"))
    return ground(extraction or _extraction(name), _page(name), taxonomy)


def _quoted_documents(grounded: Grounded) -> int:
    """Count documents whose quote grounded; the name guards (E16, E18) drop names after the quote check."""
    name_drops = grounded.diagnostics.dropped.get("data_field", 0) + grounded.diagnostics.dropped.get("generic_name", 0)
    return len(grounded.documents) + name_drops


def _kept(grounded: Grounded) -> int:
    return _quoted_documents(grounded) + len(grounded.dependencies)


@pytest.mark.parametrize("name", sorted(KEPT_AFTER))
def test_each_recorded_answer_keeps_the_pinned_number_of_items(name: str) -> None:
    """recorded · kept items per answer, after bullets and glyphs fold on both sides."""
    assert _kept(_ground(name)) == KEPT_AFTER[name]


def test_the_recorded_answers_ground_at_least_five_more_items_than_before_the_chapter() -> None:
    """recorded · the gain over the offline count taken with the previous normalisation."""
    gain = sum(KEPT_AFTER.values()) - sum(KEPT_BEFORE.values())
    assert gain >= MIN_GAIN
    assert sum(_kept(_ground(name)) for name in KEPT_BEFORE) - sum(KEPT_BEFORE.values()) >= MIN_GAIN


def _with_changed_word(extraction: PageExtraction, old: str, new: str) -> PageExtraction:
    payload = json.loads(extraction.model_dump_json())
    for item in payload["documents"]:
        item["quote"] = item["quote"].replace(old, new)
    return PageExtraction.model_validate(payload)


@pytest.mark.parametrize(
    ("name", "old", "new"),
    [
        ("aa-probebeschaeftigung", "Kundennummer", "Steuernummer"),
        ("aa-ferienbeschaeftigung", "anabin", "anabn"),
        ("aa-ferienbeschaeftigung", "Immatrikulationsbescheinigung", "Immatrikulationsbestaetigung"),
    ],
)
def test_changing_one_word_of_a_recorded_quote_makes_it_fail_again(name: str, old: str, new: str) -> None:
    """recorded · a quote that was grounded only through folding is dropped once a word is altered (negative)."""
    genuine = _ground(name)
    changed = _ground(name, _with_changed_word(_extraction(name), old, new))
    assert _quoted_documents(changed) < _quoted_documents(genuine)
    assert changed.diagnostics.dropped["quote"] > genuine.diagnostics.dropped.get("quote", 0)


def test_quotes_that_lost_their_umlauts_in_the_recorded_answer_are_still_dropped() -> None:
    """recorded · three Bundesarchiv items that the model wrote without ä, ö, ü stay dropped (negative)."""
    grounded = _ground("bundesarchiv-akteneinsicht")
    assert grounded.diagnostics.dropped["quote"] == 3
    assert {item.item.name for item in grounded.diagnostics.dropped_items if item.reason == "quote"} == {
        "AusweisApp2",
        "Antragsformular",
        "Identittsbesttigung",
    }


GROUND_SOURCES = sorted((Path(__file__).parents[1] / "discovery_ingest/extract/llm").glob("ground*.py"))
LITERAL_REASON = re.compile(r'(?:lose|keep_quoted|_lose_all)\([^)]*?"([a-z_]+)"')


def _reasons_in_source() -> set[str]:
    """Return the reason literals that the grounding code passes to ``Tally.lose`` and ``keep_quoted``."""
    return {match for path in GROUND_SOURCES for match in LITERAL_REASON.findall(path.read_text(encoding="utf-8"))}


def test_every_drop_reason_that_grounding_produces_is_assigned_to_a_class() -> None:
    """recorded · reasons seen on the recorded answers, in the name rejections and in the source all have a class."""
    seen = {reason for name in KEPT_AFTER for reason in _ground(name).diagnostics.dropped}
    reasons = seen | {reason for reason, _ in NAME_REJECTIONS} | _reasons_in_source()
    assert {"quote", "dependency_quote", "dependency_endpoint", "dependency_duplicate"} <= reasons
    assert {reason: reason_class(reason) for reason in reasons}
