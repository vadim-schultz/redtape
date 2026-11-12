"""Translate a page's blocks: each non-empty text is one unit, and the engine's answers are put back into the blocks.

A block whose text the answer lacks is left out, so the page has fewer blocks than its source and the validation refuses
it as a structural mismatch.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from discovery_ingest.snapshot_translation import Block, SourcePage
from discovery_ingest.translation.glossary import Glossary
from discovery_ingest.translation.repair import Translator
from discovery_ingest.translation.units import TranslationBatch, TranslationOutcome, TranslationUnit
from discovery_ingest.worker.translate_group import SOURCE_LOCALE

Slot = tuple[int, int]
"""The place of one text: its block's index and its index within the block (a row has one text per cell)."""


def _key(slot: Slot) -> str:
    return f"{slot[0]}.{slot[1]}"


def _units(blocks: Sequence[Block]) -> tuple[TranslationUnit, ...]:
    return tuple(
        TranslationUnit(_key((index, cell)), text, "")
        for index, block in enumerate(blocks)
        for cell, text in enumerate(block.texts)
        if text
    )


def translate_page(translator: Translator, locale: str, source: SourcePage) -> TranslationOutcome:
    """Send the non-empty texts of ``source`` to ``translator`` as one batch for ``locale``; the glossary is empty."""
    return translator.translate(TranslationBatch(SOURCE_LOCALE, locale, _units(source.blocks), Glossary()))


def _text(slot: Slot, text: str, found: Mapping[str, str]) -> str | None:
    return "" if not text else found.get(_key(slot))


def _rebuild(index: int, block: Block, found: Mapping[str, str]) -> Block | None:
    texts = [_text((index, cell), text, found) for cell, text in enumerate(block.texts)]
    kept = tuple(text for text in texts if text is not None)
    return Block(block.kind, kept) if len(kept) == len(texts) else None


def translated_blocks(source: SourcePage, outcome: TranslationOutcome) -> tuple[Block, ...]:
    """Return the blocks of ``source`` with each text replaced by its translation, in document order."""
    found = {unit.key: unit.title for unit in outcome.results}
    rebuilt = (_rebuild(index, block, found) for index, block in enumerate(source.blocks))
    return tuple(block for block in rebuilt if block is not None)
