"""Render a DOM region as compact lines of text."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from itertools import groupby

from selectolax.lexbor import LexborNode

from discovery_ingest.extract.clean_tags import BLOCK_TAGS, HEADING_TAGS, TEXT_TAG


def _is_block(node: LexborNode) -> bool:
    return node.tag in BLOCK_TAGS


def _collapse(text: str) -> str:
    return " ".join(text.split())


def _inline(node: LexborNode) -> str:
    return _collapse("".join(_inline_part(child) for child in node.iter(include_text=True)))


def _link_text(anchor: LexborNode) -> str:
    text, href = _inline(anchor), anchor.attributes.get("href") or ""
    return f"{text} ({href})" if text and href and text != href else text


def _inline_part(node: LexborNode) -> str:
    if node.tag == TEXT_TAG:
        return node.text_content or ""
    if node.tag == "a":
        return _link_text(node)
    return "".join(_inline_part(child) for child in node.iter(include_text=True))


def _flush(buffer: list[str]) -> Iterator[str]:
    line = _collapse("".join(buffer))
    buffer.clear()
    if line:
        yield line


def _heading(node: LexborNode) -> Iterator[str]:
    text = _inline(node)
    if text:
        yield f"{'#' * int((node.tag or 'h1')[1])} {text}"


def _list_item(node: LexborNode) -> Iterator[str]:
    lines = _container_lines(node)
    first = next(lines, None)
    if first is not None:
        yield f"- {first}"
    yield from lines


def _table_row(node: LexborNode) -> Iterator[str]:
    cells = (_inline(cell) for cell in node.iter() if cell.tag in ("td", "th"))
    line = " | ".join(cell for cell in cells if cell)
    if line:
        yield line


def _definition_list(node: LexborNode) -> Iterator[str]:
    term = ""
    for child in node.iter():
        if child.tag == "dt":
            term = _inline(child)
        elif child.tag == "dd" and (text := _inline(child)):
            yield f"{term}: {text}" if term else text


_BLOCK_LINES: dict[str, Callable[[LexborNode], Iterator[str]]] = {
    **dict.fromkeys(HEADING_TAGS, _heading),
    "li": _list_item,
    "tr": _table_row,
    "dl": _definition_list,
}


def _container_lines(node: LexborNode) -> Iterator[str]:
    buffer: list[str] = []
    for child in node.iter(include_text=True):
        if _is_block(child):
            yield from _flush(buffer)
            yield from _BLOCK_LINES.get(child.tag or "", _container_lines)(child)
        elif child.tag == "br":
            yield from _flush(buffer)
        else:
            buffer.append(_inline_part(child))
    yield from _flush(buffer)


def render_lines(region: LexborNode) -> list[str]:
    """Return the non-empty lines of ``region``, one per block element, without consecutive repeats."""
    return [line for line, _repeats in groupby(_container_lines(region))]
