"""Blocks of a page: each line of the cleaned text becomes one block, by its prefix, within the API's block limit."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final, Literal

from discovery_ingest.snapshot_translation.limits import MAX_BLOCK_CHARS

Kind = Literal["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "dt", "row"]
HEADING_KINDS: Final[tuple[Kind, ...]] = ("h1", "h2", "h3", "h4", "h5", "h6")
CONTROL: Final = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
ROW_SEPARATOR: Final = " | "

HEADING: Final = re.compile(r"(?P<marks>#{1,6}) (?P<text>.+)")
ITEM: Final = re.compile(r"- (?P<text>.+)")
ROW: Final = re.compile(r"(?P<cells>.+ \| .+)")
DEFINITION: Final = re.compile(r"(?P<term>[^:.!?]{1,60}): .+")
"""A ``term: text`` line. The cleaner writes definition lists as such lines, so a short label is a term."""


@dataclass(frozen=True, slots=True)
class Block:
    """One block of a page: its kind and its texts. A row's texts are its cells; every other kind has one text."""

    kind: Kind
    texts: tuple[str, ...]


def clean_text(text: str) -> str:
    """Return ``text`` with control characters replaced by spaces and every run of whitespace made one space."""
    return " ".join(CONTROL.sub(" ", text).split())


def _heading(match: re.Match[str]) -> Block:
    return Block(HEADING_KINDS[len(match["marks"]) - 1], (match["text"],))


def _item(match: re.Match[str]) -> Block:
    return Block("li", (match["text"],))


def _row(match: re.Match[str]) -> Block:
    return Block("row", tuple(match["cells"].split(ROW_SEPARATOR)))


def _definition(match: re.Match[str]) -> Block:
    return Block("dt", (match.string,))


_RULES: Final[tuple[tuple[re.Pattern[str], Callable[[re.Match[str]], Block]], ...]] = (
    (HEADING, _heading),
    (ITEM, _item),
    (ROW, _row),
    (DEFINITION, _definition),
)
"""The line prefixes in the order they are tried. A line that matches none is a paragraph."""


def _block(line: str) -> Block:
    for pattern, build in _RULES:
        if (match := pattern.fullmatch(line)) is not None:
            return build(match)
    return Block("p", (line,))


def _split_text(text: str, limit: int) -> list[str]:
    """Cut ``text`` into pieces of at most ``limit`` characters, at the last space before the limit if any."""
    pieces: list[str] = []
    while len(text) > limit:
        cut = text.rfind(" ", 0, limit + 1)
        cut = cut if cut > 0 else limit
        pieces.append(text[:cut])
        text = text[cut:].lstrip(" ")
    return [*pieces, text]


def _pack(cells: list[str], limit: int) -> list[list[str]]:
    """Group consecutive cells into rows whose cells together stay within ``limit`` characters."""
    groups: list[list[str]] = []
    for cell in cells:
        if groups and sum(len(part) for part in groups[-1]) + len(cell) <= limit:
            groups[-1].append(cell)
        else:
            groups.append([cell])
    return groups


def _within_limit(block: Block) -> list[Block]:
    """Return ``block`` as blocks within the limit: a text is cut, and a row's cells are cut and packed into rows."""
    if block.kind != "row":
        return [Block(block.kind, (piece,)) for piece in _split_text(block.texts[0], MAX_BLOCK_CHARS)]
    cells = [piece for cell in block.texts for piece in _split_text(cell, MAX_BLOCK_CHARS)]
    return [Block("row", tuple(group)) for group in _pack(cells, MAX_BLOCK_CHARS)]


def page_blocks(text: str) -> tuple[Block, ...]:
    """Return the blocks of cleaned ``text`` in document order: one per non-blank line, each within the limit."""
    lines = (clean_text(line) for line in text.split("\n"))
    return tuple(piece for line in lines if line for piece in _within_limit(_block(line)))
