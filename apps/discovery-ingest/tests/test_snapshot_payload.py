"""Payload of a translated page: canonical JSON, the cap and the block limits, and the page assembly around them."""

from __future__ import annotations

import json

from discovery_ingest.snapshot_translation.blocks import Block
from discovery_ingest.snapshot_translation.limits import DOCUMENT_MAX_CHARS, MAX_BLOCK_CHARS, MAX_BLOCKS
from discovery_ingest.snapshot_translation.page import SourcePage, finish_page, prepare_page
from discovery_ingest.snapshot_translation.payload import TranslatedPage, canonical_payload
from discovery_ingest.snapshot_translation.validate_blocks import Rejected

URL = "https://portal.example/dienst/antrag"
LONG = "Bitte bringen Sie alle erforderlichen Unterlagen zum Termin mit. " * 4


def _html(body: str) -> str:
    return f"<html lang='de'><body>{body}</body></html>"


def _identity(html: str) -> TranslatedPage:
    source = prepare_page(html, URL)
    assert isinstance(source, SourcePage)
    result = finish_page(source, source.blocks)
    assert isinstance(result, TranslatedPage)
    return result


def _body(html: str) -> dict:
    return json.loads(canonical_payload(_identity(html)))


def test_the_document_cap_is_its_own_constant_of_30000_characters() -> None:
    assert DOCUMENT_MAX_CHARS == 30_000


def test_identical_input_produces_byte_identical_canonical_json() -> None:
    html = _html(f"<p>{LONG}</p><table><tr><td>Name</td><td>Wert</td></tr></table>")
    first, second = canonical_payload(_identity(html)), canonical_payload(_identity(html))
    assert first == second
    assert first == json.dumps(json.loads(first), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def test_the_payload_has_the_five_fields_and_the_api_block_shapes() -> None:
    html = _html(
        f"<p>{LONG}</p><table><tr><td>Name</td><td>Wert</td></tr></table><dl><dt>Begriff</dt><dd>Text</dd></dl>"
    )
    body = _body(html)
    assert set(body) == {"unit", "source_hash", "truncated", "source_url", "blocks"}
    assert body["unit"] == "snapshot"
    assert body["source_url"] == URL
    assert body["truncated"] is False
    assert {"kind": "row", "cells": ["Name", "Wert"]} in body["blocks"]
    assert {"kind": "dt", "text": "Begriff: Text"} in body["blocks"]


def test_a_page_over_the_cap_has_truncated_set_and_keeps_blocks_in_document_order() -> None:
    sections = "".join(f"<h2>Abschnitt {number:03d}</h2><p>{'Text ' * 200}</p>" for number in range(40))
    body = _body(_html(sections))
    assert body["truncated"] is True
    numbers = [int(block["text"].rsplit(" ", 1)[1]) for block in body["blocks"] if block["kind"] == "h2"]
    assert numbers and numbers == sorted(numbers)


def test_a_page_under_the_cap_is_not_truncated() -> None:
    assert _body(_html(f"<p>{LONG}</p>"))["truncated"] is False


def test_more_than_2000_blocks_keep_the_first_2000_and_set_truncated() -> None:
    paragraphs = "".join(f"<p>Zeile {number}</p>" for number in range(2100))
    body = _body(_html(f"<p>{LONG}</p>{paragraphs}"))
    blocks = body["blocks"]
    assert len(blocks) == MAX_BLOCKS
    assert body["truncated"] is True
    assert blocks[-1] == {"kind": "p", "text": f"Zeile {MAX_BLOCKS - 2}"}


def test_the_untranslated_count_is_reported_and_the_german_text_is_kept() -> None:
    source = prepare_page(_html(f"<p>{LONG}</p><p>Zweiter Absatz mit Inhalt.</p>"), URL)
    assert isinstance(source, SourcePage)
    result = finish_page(source, (Block("p", ("Please bring all the documents. " * 8,)), Block("p", ("",))))
    assert isinstance(result, TranslatedPage)
    assert result.untranslated == 1
    assert result.blocks[1] == Block("p", ("Zweiter Absatz mit Inhalt.",))


def test_a_translation_with_the_wrong_block_count_is_rejected() -> None:
    source = prepare_page(_html(f"<p>{LONG}</p><p>Zweiter Absatz mit Inhalt.</p>"), URL)
    assert isinstance(source, SourcePage)
    assert isinstance(finish_page(source, source.blocks[:1]), Rejected)


def test_every_block_of_a_payload_is_within_the_api_limits() -> None:
    html = _html(
        f"<p>{LONG}</p>"
        f"<p>{' '.join(['wort'] * 1500)}</p>"
        f"<table><tr><td>{' '.join(['alpha'] * 500)}</td><td>{' '.join(['beta'] * 500)}</td></tr></table>"
        "<p>Steuer\x01zeichen im Text</p>"
    )
    blocks = _body(html)["blocks"]
    for block in blocks:
        cells = block.get("cells", [block.get("text")])
        assert sum(len(cell) for cell in cells) <= MAX_BLOCK_CHARS
        assert all(cell.strip() and "\x01" not in cell for cell in cells)
    assert len(blocks) <= MAX_BLOCKS
