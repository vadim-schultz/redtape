"""The gold set loader and the cleaner recall, on a tiny gold set built in the test (chapter E5, loop A)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from discovery_ingest.extract.llm.evaluation.gold import GoldError, GoldPage, load_gold
from discovery_ingest.extract.llm.evaluation.metrics import cleaner_recall

PAGE = "<html lang='de'><body><main><h1>Antrag</h1><p>Bitte bringen Sie Ihren Reisepass mit.</p></main></body></html>"
GOLD = {
    "source_url": "https://portal.example/antrag",
    "page_kind": "service",
    "documents": [{"name": "Reisepass", "role": "required", "condition": "bei Zuzug", "is_optional": True}],
    "dependencies": [{"parent": "Antrag", "requires": "Reisepass"}],
    "category_codes": ["home-and-housing"],
}


def _write(directory: Path, name: str, gold: object = GOLD, html: str | None = PAGE) -> None:
    (directory / f"{name}.gold.json").write_text(json.dumps(gold), encoding="utf-8")
    if html is not None:
        (directory / f"{name}.html").write_text(html, encoding="utf-8")


def test_the_loader_pairs_each_html_with_its_gold_labels_in_name_order(tmp_path: Path) -> None:
    """load_gold · each page carries its decoded html and labels; --limit keeps the first pages by name."""
    _write(tmp_path, "b-page")
    _write(tmp_path, "a-page")

    pages = load_gold(tmp_path)

    assert [page.name for page in pages] == ["a-page", "b-page"]
    first = pages[0]
    assert isinstance(first, GoldPage) and "Reisepass" in first.html
    assert first.documents[0].condition == "bei Zuzug" and first.documents[0].is_optional
    assert [page.name for page in load_gold(tmp_path, limit=1)] == ["a-page"]


def test_the_loader_rejects_a_missing_page_an_unknown_role_and_a_missing_directory(tmp_path: Path) -> None:
    """load_gold · a gold file without html, a role outside the schema and no directory raise GoldError naming the page."""
    _write(tmp_path, "no-html", html=None)
    with pytest.raises(GoldError, match="no-html"):
        load_gold(tmp_path)
    (tmp_path / "no-html.gold.json").unlink()
    _write(tmp_path, "bad-role", gold={**GOLD, "documents": [{"name": "X", "role": "boss"}]})
    with pytest.raises(GoldError, match="bad-role"):
        load_gold(tmp_path)
    with pytest.raises(GoldError, match="not a directory"):
        load_gold(tmp_path / "missing")


def test_cleaner_recall_counts_gold_names_whose_slug_is_in_the_cleaned_text() -> None:
    """cleaner_recall · a name found as whole words counts, pooled over pages, whatever the case or accents."""
    pages = [
        (["Reisepass", "Meldebescheinigung"], "Bitte bringen Sie Ihren REISEPASS mit."),
        (["Führungszeugnis"], "Das Fuehrungszeugnis wird nicht verlangt, ein Führungszeugnis schon."),
    ]

    assert cleaner_recall(pages) == pytest.approx(2 / 3)


def test_cleaner_recall_does_not_count_a_name_inside_a_longer_word_and_a_page_without_names_is_full() -> None:
    """cleaner_recall · 'Pass' is not found in 'Reisepass'; with no gold names the recall is 1, not a division by zero."""
    assert cleaner_recall([(["Pass"], "Bitte den Reisepass mitbringen")]) == 0.0
    assert cleaner_recall([([], "irgendein Text")]) == 1.0
    assert cleaner_recall([]) == 1.0
