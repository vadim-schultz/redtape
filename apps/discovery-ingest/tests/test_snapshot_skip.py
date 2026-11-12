"""Skip decision and source hash of a snapshot page: a skip carries its reason and never raises."""

from __future__ import annotations

import hashlib

from discovery_ingest.extract.clean import CLEAN_VERSION
from discovery_ingest.snapshot_translation.hash import source_hash
from discovery_ingest.snapshot_translation.page import SkippedPage, prepare_page
from discovery_ingest.snapshot_translation.skip import SkipReason, skip_reason

URL = "https://portal.example/dienst/antrag"
LONG = "Bitte bringen Sie alle erforderlichen Unterlagen zum Termin mit. " * 4


def _page(body: str, lang: str | None = "de") -> str:
    attribute = "" if lang is None else f' lang="{lang}"'
    return f"<html{attribute}><head><title>Antrag</title></head><body>{body}</body></html>"


def _skip_of(html: str) -> SkipReason:
    result = prepare_page(html, URL)
    assert isinstance(result, SkippedPage), "the page should have been skipped"
    return result.reason


def test_a_javascript_shell_under_200_characters_is_skipped_as_too_short() -> None:
    shell = '<div id="root"></div><script>window.app = {};</script><p>Bitte JavaScript aktivieren.</p>'
    assert _skip_of(_page(shell)) is SkipReason.TOO_SHORT


def test_the_200_character_boundary_separates_too_short_from_a_translated_page() -> None:
    assert skip_reason("x" * 199, "de") is SkipReason.TOO_SHORT
    assert skip_reason("x" * 200, "de") is None


def test_a_page_in_another_language_is_skipped_as_not_german() -> None:
    assert _skip_of(_page(f"<p>{LONG}</p>", lang="en")) is SkipReason.NOT_GERMAN


def test_a_regional_german_tag_counts_as_german() -> None:
    assert not isinstance(prepare_page(_page(f"<p>{LONG}</p>", lang="de-AT"), URL), SkippedPage)


def test_a_page_that_declares_no_language_is_skipped_as_not_german() -> None:
    assert _skip_of(_page(f"<p>{LONG}</p>", lang=None)) is SkipReason.NOT_GERMAN


def test_empty_html_is_skipped_as_too_short_and_does_not_raise() -> None:
    assert _skip_of("") is SkipReason.TOO_SHORT


def test_a_short_page_is_too_short_even_when_it_is_not_german() -> None:
    assert _skip_of(_page("<p>Hello</p>", lang="en")) is SkipReason.TOO_SHORT


def test_the_skip_reasons_are_the_values_the_api_accepts() -> None:
    assert {reason.value for reason in SkipReason} == {"too_short", "not_german"}


def test_the_hash_is_sha256_over_the_text_a_nul_byte_and_the_clean_version() -> None:
    expected = hashlib.sha256(b"Text\x00" + CLEAN_VERSION.encode("utf-8")).hexdigest()
    assert source_hash("Text") == expected


def test_the_same_cleaned_text_gives_the_same_hash_when_only_nonces_differ() -> None:
    first = _page(f"<script nonce='aaa'>var t = 1;</script><p>{LONG}</p>")
    second = _page(f"<script nonce='bbb'>var t = 1;</script><meta name='csp-nonce' content='ccc'><p>{LONG}</p>")
    assert prepare_page(first, URL).source_hash == prepare_page(second, URL).source_hash


def test_the_hash_changes_when_the_cleaned_text_changes() -> None:
    assert source_hash(LONG) != source_hash(LONG + "x")
