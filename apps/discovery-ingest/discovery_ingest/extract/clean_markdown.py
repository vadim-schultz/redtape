"""Render a DOM region as compact lines of text."""

from __future__ import annotations

from collections.abc import Iterator

from selectolax.lexbor import LexborNode

BLOCK_TAGS = frozenset(
    {
        "address",
        "article",
        "blockquote",
        "body",
        "button",
        "caption",
        "dd",
        "details",
        "dl",
        "dt",
        "div",
        "fieldset",
        "figcaption",
        "figure",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "hr",
        "li",
        "main",
        "ol",
        "p",
        "pre",
        "section",
        "summary",
        "table",
        "tbody",
        "td",
        "tfoot",
        "th",
        "thead",
        "tr",
        "ul",
    }
)
TEXT_TAG = "-text"


def _is_block(node: LexborNode) -> bool:
    return node.tag in BLOCK_TAGS


def _inline_part(node: LexborNode) -> str:
    if node.tag == TEXT_TAG:
        return node.text_content or ""
    return "".join(_inline_part(child) for child in node.iter(include_text=True))


def _collapse(text: str) -> str:
    return " ".join(text.split())


def _flush(buffer: list[str]) -> Iterator[str]:
    line = _collapse("".join(buffer))
    buffer.clear()
    if line:
        yield line


def _container_lines(node: LexborNode) -> Iterator[str]:
    buffer: list[str] = []
    for child in node.iter(include_text=True):
        if _is_block(child):
            yield from _flush(buffer)
            yield from _container_lines(child)
        elif child.tag == "br":
            yield from _flush(buffer)
        else:
            buffer.append(_inline_part(child))
    yield from _flush(buffer)


def render_lines(region: LexborNode) -> list[str]:
    """Return the non-empty lines of ``region``, one per block element."""
    return list(_container_lines(region))
