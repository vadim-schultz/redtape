"""Golden snapshot pages: the expected blocks of translated pages, and the skip of pages that must not be translated."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from discovery_ingest.snapshot_translation.page import SkippedPage, finish_page, prepare_page
from discovery_ingest.snapshot_translation.payload import TranslatedPage, canonical_payload

FIXTURES = Path(__file__).parent / "fixtures" / "snapshot_gold"
MANIFEST: dict[str, str] = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
NAMES = sorted(MANIFEST)


def _actual(name: str) -> dict:
    html = (FIXTURES / f"{name}.html").read_text(encoding="utf-8")
    result = prepare_page(html, MANIFEST[name])
    if isinstance(result, SkippedPage):
        return {"skipped": result.reason.value, "source_hash": result.source_hash}
    translated = finish_page(result, result.blocks)
    assert isinstance(translated, TranslatedPage), f"{name}: the identity translation was rejected"
    return json.loads(canonical_payload(translated))


def test_the_golden_set_has_translated_and_skipped_pages() -> None:
    outcomes = {"skipped" in _actual(name) for name in NAMES}
    assert outcomes == {True, False}


@pytest.mark.parametrize("name", NAMES)
def test_a_golden_page_produces_its_expected_result(name: str) -> None:
    expected = json.loads((FIXTURES / f"{name}.expected.json").read_text(encoding="utf-8"))
    assert _actual(name) == expected


@pytest.mark.parametrize("name", NAMES)
def test_no_link_token_is_left_in_a_golden_result(name: str) -> None:
    assert "⟦" not in json.dumps(_actual(name), ensure_ascii=False)
