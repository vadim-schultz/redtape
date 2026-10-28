"""Screen-reader helper text on the committed real pages: it is gone, and nothing the gold labels name goes with it."""

from __future__ import annotations

from pathlib import Path

from discovery_ingest.extract.clean import clean_page
from discovery_ingest.extract.llm.evaluation.gold import GoldPage, load_gold
from discovery_ingest.extract.llm.evaluation.metrics import cleaner_recall

GOLD_DIR = Path(__file__).parent / "fixtures" / "gold"
LABEL = "positiv:"


def _arbeitsagentur_pages() -> list[GoldPage]:
    return [page for page in load_gold(GOLD_DIR) if "arbeitsagentur.de" in page.source_url]


def _cleaned(page: GoldPage) -> str:
    return clean_page(page.html, page.source_url).text


def test_the_committed_arbeitsagentur_gold_pages_no_longer_contain_the_positiv_label() -> None:
    """gold set · ``<span class="sr-only">positiv:</span>`` of ``ul.ba-list-positive`` is not page text."""
    pages = _arbeitsagentur_pages()

    assert any(LABEL in page.html for page in pages), "the fixtures must still carry the screen-reader label"
    assert [page.name for page in pages if LABEL in _cleaned(page)] == []


def test_dropping_helper_text_keeps_every_gold_name_and_leaves_no_real_page_empty() -> None:
    """gold set · cleaner_recall stays 47 of 47 and only the un-rendered shell cleans to nothing."""
    pages = load_gold(GOLD_DIR)
    recall = cleaner_recall([([d.name for d in page.documents], _cleaned(page)) for page in pages])

    assert recall == 1.0
    assert [page.name for page in pages if not _cleaned(page).strip()] == ["verwaltung-js-shell"]
