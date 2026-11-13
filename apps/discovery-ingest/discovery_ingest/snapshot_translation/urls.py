"""Link tokens: each link in a page becomes a token before translation, and is put back byte-for-byte after it."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from typing import Final

from discovery_ingest.snapshot_translation.blocks import Block
from discovery_ingest.translation import tokens

LINK: Final = re.compile(r"(\(https?://\S+\)|https?://\S+)")
"""A link as the cleaner writes it: ``text (https://…)`` or a bare URL.

The group keeps each link when the text is split.
"""


def token_ids(text: str) -> Counter[str]:
    """Return the token numbers that ``text`` contains, with their counts."""
    return Counter(tokens.PROTECTED.findall(text))


def _token(index: int) -> str:
    return f"⟦{index}⟧"


def _protect_text(text: str, urls: list[str]) -> str:
    """Replace each link of ``text`` by the next token and append the link to ``urls``."""
    parts = LINK.split(text)
    for index in range(1, len(parts), 2):
        urls.append(parts[index])
        parts[index] = _token(len(urls) - 1)
    return "".join(parts)


def protect_urls(blocks: Sequence[Block]) -> tuple[tuple[Block, ...], tuple[str, ...]]:
    """Return ``blocks`` with every link replaced by a token, and the links in token order.

    The numbering runs over the whole page, so one list of links restores every block of it.
    """
    urls: list[str] = []
    protected = tuple(Block(block.kind, tuple(_protect_text(text, urls) for text in block.texts)) for block in blocks)
    return protected, tuple(urls)


def restore_block(block: Block, urls: Sequence[str]) -> Block:
    """Return ``block`` with each token put back as the link it stands for."""
    return Block(block.kind, tuple(tokens.restore(text, urls) for text in block.texts))
