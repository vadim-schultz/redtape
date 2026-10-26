"""Split xZufi HTML into plain fragments: leaf list items or line-separated paragraphs."""

from __future__ import annotations

import re

from selectolax.lexbor import LexborHTMLParser, LexborNode

_BREAK = re.compile(r"<br\s*/?>", re.IGNORECASE)
_LEADING = re.compile(r"^(?:[-–—•·*▪]+\s*|\(?\d{1,2}[.)]\s+|[a-z]\)\s+)")
_TRAILING = re.compile(r"(?:\s+(?:oder|und|sowie))?[\s;,.]*$", re.IGNORECASE)


def _parse(html: str) -> LexborHTMLParser:
    return LexborHTMLParser(_BREAK.sub("\n", html))


def collapse(text: str) -> str:
    """Collapse every whitespace run, non-breaking spaces included, to one space."""
    return " ".join(text.split())


def _strip_bullets(text: str) -> str:
    return _LEADING.sub("", text)


def _strip_list_punctuation(text: str) -> str:
    return _TRAILING.sub("", text)


def plain_text(html: str) -> str:
    """Return the visible text of ``html`` with collapsed whitespace."""
    body = _parse(html).body
    return collapse(body.text(separator=" ")) if body is not None else ""


def _leaf_items(tree: LexborHTMLParser) -> list[LexborNode]:
    """List items without a nested list item: the parent of a nested list only labels its children."""
    return [item for item in tree.css("li") if len(item.css("li")) == 1]


def list_items(html: str) -> list[str]:
    """Return the cleaned text of every leaf list item, without bullets or trailing connectives."""
    cleaned = (_strip_bullets(collapse(item.text(separator=" "))) for item in _leaf_items(_parse(html)))
    return [_strip_list_punctuation(text) for text in cleaned]


def paragraph_lines(html: str) -> list[str]:
    """Return the text lines of every paragraph (or of the body when there is none), punctuation kept."""
    tree = _parse(html)
    blocks = tree.css("p") or ([tree.body] if tree.body is not None else [])
    lines = (line for block in blocks for line in block.text().splitlines())
    return [_strip_bullets(collapse(line)) for line in lines]
