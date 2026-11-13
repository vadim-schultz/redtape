"""Blocks of a snapshot page: line prefixes become block kinds, and no block breaks the API's limits."""

from __future__ import annotations

from discovery_ingest.snapshot_translation.blocks import Block, page_blocks
from discovery_ingest.snapshot_translation.limits import MAX_BLOCK_CHARS
from discovery_ingest.snapshot_translation.page import SourcePage, prepare_page

URL = "https://portal.example/dienst/antrag"
LONG = "Bitte bringen Sie alle erforderlichen Unterlagen zum Termin mit. " * 4


def _kinds(text: str) -> list[str]:
    return [block.kind for block in page_blocks(text)]


def test_line_prefixes_become_heading_list_row_term_and_paragraph_blocks() -> None:
    text = "\n".join(
        [
            "# Eins",
            "## Zwei",
            "### Drei",
            "#### Vier",
            "##### Fünf",
            "###### Sechs",
            "- Punkt",
            "Name | Wert",
            "Begriff: Erklärung",
            "Ein Absatz.",
        ]
    )
    blocks = page_blocks(text)
    assert [block.kind for block in blocks] == ["h1", "h2", "h3", "h4", "h5", "h6", "li", "row", "dt", "p"]
    assert blocks[0] == Block("h1", ("Eins",))
    assert blocks[6] == Block("li", ("Punkt",))
    assert blocks[7] == Block("row", ("Name", "Wert"))
    assert blocks[8] == Block("dt", ("Begriff: Erklärung",))


def test_a_cleaned_html_page_yields_the_blocks_of_its_lines() -> None:
    body = (
        "<h1>Eins</h1><h2>Zwei</h2><h3>Drei</h3><h4>Vier</h4><h5>Fünf</h5><h6>Sechs</h6>"
        f"<p>{LONG}</p>"
        "<ul><li>Punkt eins</li><li>Punkt zwei</li></ul>"
        "<table><tr><td>Name</td><td>Wert</td></tr><tr><td>A</td><td>1</td></tr></table>"
        "<dl><dt>Begriff</dt><dd>Erklärung hier</dd></dl>"
    )
    result = prepare_page(f"<html lang='de'><body>{body}</body></html>", URL)
    assert isinstance(result, SourcePage)
    assert [block.kind for block in result.blocks] == [
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "li",
        "li",
        "row",
        "row",
        "dt",
    ]


def test_a_seventh_hash_or_a_hash_without_a_space_is_a_paragraph() -> None:
    assert _kinds("####### Text\n#1 Ticket") == ["p", "p"]


def test_a_sentence_before_a_colon_is_a_paragraph_not_a_term() -> None:
    assert _kinds("Dies ist ein Satz. Er endet: hier") == ["p"]


def test_control_characters_are_removed_and_a_line_of_only_controls_makes_no_block() -> None:
    blocks = page_blocks("Text\x01 mit\x7f Steuer\n\x01\x02\n\x0b")
    assert blocks == (Block("p", ("Text mit Steuer",)),)


def test_a_paragraph_over_the_limit_is_cut_at_spaces_into_paragraphs_within_it() -> None:
    text = " ".join(["wort"] * 1500)
    blocks = page_blocks(text)
    assert len(blocks) > 1
    assert all(block.kind == "p" and len(block.texts[0]) <= MAX_BLOCK_CHARS for block in blocks)
    assert " ".join(block.texts[0] for block in blocks) == text


def test_a_row_over_the_limit_is_packed_into_rows_within_it() -> None:
    cells = [" ".join(["alpha"] * 500)] * 3
    blocks = page_blocks(" | ".join(cells))
    assert all(block.kind == "row" for block in blocks)
    assert all(sum(len(cell) for cell in block.texts) <= MAX_BLOCK_CHARS for block in blocks)
    assert [cell for block in blocks for cell in block.texts] == cells


def test_a_single_word_longer_than_the_limit_is_cut_into_pieces() -> None:
    blocks = page_blocks("x" * 9000)
    assert [len(block.texts[0]) for block in blocks] == [4000, 4000, 1000]
