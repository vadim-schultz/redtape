"""Extractor registry lookup and charset-safe decoding (chapter 17, Loop A)."""

from __future__ import annotations

import pytest
from discovery_ingest.extract.decode import decode_html
from discovery_ingest.extract.registry import EXTRACTORS, find_extractor

from extract_fakes import FakeExtractor

URL = "https://portal.example/service/1"


def test_find_extractor_returns_the_first_matching_extractor() -> None:
    """find_extractor · the first match in registry order wins, whatever follows."""
    first, second = FakeExtractor("first"), FakeExtractor("second")
    other = FakeExtractor("other", host="elsewhere.example")

    assert find_extractor(URL, "text/html", (other, first, second)) is first


@pytest.mark.parametrize("content_type", ["text/html", None])
def test_find_extractor_returns_none_when_nothing_matches_and_the_production_registry_is_empty(
    content_type: str | None,
) -> None:
    """find_extractor · no match (or an empty registry) is None, never an error."""
    other = FakeExtractor(host="elsewhere.example")

    assert find_extractor(URL, content_type, (other,)) is None
    assert find_extractor(URL, content_type) is None
    assert EXTRACTORS == ()


@pytest.mark.parametrize(
    ("body", "content_type", "expected"),
    [
        ("Bürger".encode("iso-8859-1"), "text/html; charset=ISO-8859-1", "Bürger"),
        ("Bürger".encode("iso-8859-1"), 'text/html; charset="latin-1"', "Bürger"),
        ('<meta charset="windows-1252">Bürger'.encode("cp1252"), "text/html", '<meta charset="windows-1252">Bürger'),
        (
            '<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">ä'.encode("latin-1"),
            None,
            '<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">ä',
        ),
        ("Bürger".encode(), "text/html; charset=utf-8", "Bürger"),
    ],
)
def test_decode_uses_the_declared_charset_then_the_meta_charset(
    body: bytes, content_type: str | None, expected: str
) -> None:
    """decode · the Content-Type charset, then a meta charset, decode the bytes to the right text."""
    assert decode_html(body, content_type) == expected


def test_decode_prefers_the_header_charset_over_the_meta_charset() -> None:
    """decode · the header wins when both name a charset."""
    body = '<meta charset="utf-8">Bürger'.encode("latin-1")

    assert decode_html(body, "text/html; charset=latin-1") == '<meta charset="utf-8">Bürger'


@pytest.mark.parametrize(
    ("body", "content_type"),
    [
        (b"B\xfcrger", None),
        (b"B\xfcrger", "text/html; charset=no-such-charset"),
        (b'<meta charset="no-such-charset">B\xfcrger', "text/html"),
        (b"B\xfcrger", "text/html; charset=utf-8"),
    ],
)
def test_decode_falls_back_to_utf8_with_replacement(body: bytes, content_type: str | None) -> None:
    """decode · an unknown charset or undecodable bytes end in UTF-8 with U+FFFD, never an exception."""
    assert "B�rger" in decode_html(body, content_type)


def test_decode_strips_nul_bytes_and_keeps_the_rest() -> None:
    """decode · NUL characters are removed, also when the charset is multi-byte."""
    assert decode_html(b"a\x00b<p>c\x00</p>", "text/html") == "ab<p>c</p>"
    assert decode_html("a\x00b".encode("utf-16-le"), "text/html; charset=utf-16-le") == "ab"
