"""URL tokens: a link is replaced by a token before translation and restored byte-for-byte after it."""

from __future__ import annotations

from collections import Counter

from discovery_ingest.snapshot_translation.blocks import Block, page_blocks
from discovery_ingest.snapshot_translation.urls import protect_urls, restore_block, token_ids
from discovery_ingest.translation import tokens


def test_a_link_is_replaced_by_a_token_and_restored_byte_for_byte() -> None:
    text = "Antrag (https://a.de/x?y=1&z=%C3%BC) bitte"
    blocks, urls = protect_urls(page_blocks(text))
    assert blocks == (Block("p", ("Antrag ⟦0⟧ bitte",)),)
    assert urls == ("(https://a.de/x?y=1&z=%C3%BC)",)
    assert restore_block(blocks[0], urls) == Block("p", (text,))


def test_a_parenthesis_inside_a_link_stays_inside_its_token() -> None:
    text = "Siehe Link (https://portal.example/a/b_(c)) und weiter"
    blocks, urls = protect_urls(page_blocks(text))
    assert restore_block(blocks[0], urls).texts == (text,)
    assert "(c)" not in blocks[0].texts[0]


def test_a_bare_url_is_protected_and_restored_too() -> None:
    text = "Seite https://x.de/y Ende"
    blocks, urls = protect_urls(page_blocks(text))
    assert blocks[0].texts == ("Seite ⟦0⟧ Ende",)
    assert restore_block(blocks[0], urls).texts == (text,)


def test_tokens_are_numbered_across_the_page_in_document_order() -> None:
    blocks, urls = protect_urls(page_blocks("Erst (https://a.de) hier\nZweit (https://b.de) dort"))
    assert [block.texts[0] for block in blocks] == ["Erst ⟦0⟧ hier", "Zweit ⟦1⟧ dort"]
    assert urls == ("(https://a.de)", "(https://b.de)")


def test_a_text_without_links_is_unchanged_and_has_no_urls() -> None:
    blocks, urls = protect_urls(page_blocks("Ohne Link."))
    assert blocks == (Block("p", ("Ohne Link.",)),)
    assert urls == ()


def test_the_token_is_the_one_the_translation_tokens_module_reads() -> None:
    blocks, _urls = protect_urls(page_blocks("Antrag (https://a.de) bitte"))
    assert tokens.PROTECTED.findall(blocks[0].texts[0]) == ["0"]
    assert token_ids(blocks[0].texts[0]) == Counter({"0": 1})
