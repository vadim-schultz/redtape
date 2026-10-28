"""Recall and token-saving gate of the page cleaner on the rendered-snapshot fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from discovery_ingest.extract.clean import clean_page

PAGES = Path(__file__).parent / "fixtures" / "pages"
BASE = "https://portal.example/dienst/"
MAX_AVERAGE_RATIO = 0.40
NAMES = sorted(path.name.removesuffix(".facts.json") for path in PAGES.glob("*.facts.json"))


def _clean(name: str) -> str:
    return clean_page((PAGES / f"{name}.html").read_text(encoding="utf-8"), BASE).text


def _facts(name: str) -> list[str]:
    return json.loads((PAGES / f"{name}.facts.json").read_text(encoding="utf-8"))


def _missing(name: str) -> list[str]:
    text = _clean(name)
    return [fact for fact in _facts(name) if fact not in text]


def test_the_fixture_set_covers_five_to_eight_pages() -> None:
    assert 5 <= len(NAMES) <= 8


@pytest.mark.parametrize("name", NAMES)
def test_every_expected_fact_of_every_fixture_survives_cleaning(name: str) -> None:
    assert _missing(name) == [], f"{name}: facts lost by the cleaner"


def test_recall_over_all_listed_facts_is_one() -> None:
    lost = {name: _missing(name) for name in NAMES if _missing(name)}
    total = sum(len(_facts(name)) for name in NAMES)
    recall = 1 - sum(map(len, lost.values())) / total
    assert recall == 1.0, f"recall {recall:.3f}, lost: {lost}"


def test_cleaned_text_is_at_most_40_percent_of_the_raw_text_on_average() -> None:
    ratios = {name: len(_clean(name)) / len((PAGES / f"{name}.html").read_text(encoding="utf-8")) for name in NAMES}
    average = sum(ratios.values()) / len(ratios)
    assert average <= MAX_AVERAGE_RATIO, f"average ratio {average:.3f}; per page {ratios}"


def test_the_javascript_shell_snapshot_yields_more_text_than_its_raw_response() -> None:
    raw = clean_page((PAGES / "js_shell.raw.html").read_text(encoding="utf-8"), BASE).text
    assert len(_clean("js_shell")) > len(raw)
    assert raw == ""
