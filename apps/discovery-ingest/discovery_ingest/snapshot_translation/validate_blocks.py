"""Checks of translated blocks against their source blocks.

A translated page must have the source's block count and kinds, or it is refused whole. Each block is then checked on
its own, and a block that fails keeps its German text, with the link tokens put back, and the reason it failed.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Final

from discovery_ingest.snapshot_translation.blocks import Block, clean_text
from discovery_ingest.snapshot_translation.limits import MAX_BLOCK_CHARS
from discovery_ingest.snapshot_translation.urls import restore_block, token_ids
from discovery_ingest.translation.findings import Check
from discovery_ingest.translation.validate import length_ratio, non_empty


@dataclass(frozen=True, slots=True)
class Rejected:
    """A translated page refused as a whole, because its blocks do not have the source's count or kinds."""

    reason: str


@dataclass(frozen=True, slots=True)
class CheckedBlock:
    """One block to store: the translation when it passed every check, otherwise the German source.

    ``problem`` says why the translation was refused, and is ``None`` when it was kept.
    """

    block: Block
    problem: str | None

    @property
    def untranslated(self) -> bool:
        """Whether the German text was kept in place of a translation."""
        return self.problem is not None


BlockCheck = Callable[[Block, Block, Sequence[str]], str | None]
"""A check of one translated block against its source: ``(source, translated, urls)`` to a problem, or ``None``."""


def _tokens_survive(source: str, translated: str) -> str | None:
    if token_ids(source) == token_ids(translated):
        return None
    return "a link token was lost or invented"


TEXT_CHECKS: Final[tuple[Check, ...]] = (non_empty, length_ratio, _tokens_survive)


def _text_problem(source: str, translated: str) -> str | None:
    return next((problem for check in TEXT_CHECKS if (problem := check(source, translated))), None)


def _same_cells(source: Block, translated: Block, _urls: Sequence[str]) -> str | None:
    if len(source.texts) != len(translated.texts):
        return "the translation has a different number of cells"
    return None


def _texts_pass(source: Block, translated: Block, _urls: Sequence[str]) -> str | None:
    pairs = zip(source.texts, translated.texts, strict=True)
    return next((problem for s, t in pairs if (problem := _text_problem(s, t))), None)


def _within_limit(_source: Block, translated: Block, urls: Sequence[str]) -> str | None:
    restored = restore_block(translated, urls)
    if sum(len(text) for text in restored.texts) > MAX_BLOCK_CHARS:
        return f"the translation is over {MAX_BLOCK_CHARS} characters"
    return None


BLOCK_CHECKS: Final[tuple[BlockCheck, ...]] = (_same_cells, _texts_pass, _within_limit)


def _block_problem(source: Block, translated: Block, urls: Sequence[str]) -> str | None:
    return next((problem for check in BLOCK_CHECKS if (problem := check(source, translated, urls))), None)


def _check_block(source: Block, translated: Block, urls: Sequence[str]) -> CheckedBlock:
    cleaned = Block(translated.kind, tuple(clean_text(text) for text in translated.texts))
    problem = _block_problem(source, cleaned, urls)
    chosen = source if problem is not None else cleaned
    return CheckedBlock(restore_block(chosen, urls), problem)


def check_page(
    source: Sequence[Block], translated: Sequence[Block], urls: Sequence[str]
) -> tuple[CheckedBlock, ...] | Rejected:
    """Check each translated block against its source block, or refuse the page when its structure differs.

    ``urls`` are the links of the source page, in token order. The result holds one block per source block, in order.
    """
    if not translated:
        return Rejected("a translated page has at least one block")
    if len(source) != len(translated):
        return Rejected(f"the translation has {len(translated)} blocks, the source has {len(source)}")
    if [block.kind for block in source] != [block.kind for block in translated]:
        return Rejected("the translated block kinds differ from the source's")
    return tuple(_check_block(s, t, urls) for s, t in zip(source, translated, strict=True))
