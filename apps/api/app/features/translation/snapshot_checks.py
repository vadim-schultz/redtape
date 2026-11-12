"""The ordered checks a posted page result passes before anything is written; the first refusal settles the item."""

from __future__ import annotations

import enum
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from app.features.discovery.artifact_read import LatestSnapshot
from app.models.snapshot_translation import SnapshotTranslation, SnapshotTranslationTask
from app.schema.suggestion.payload import validate_i18n_value
from app.schema.translation.snapshot_machine import (
    RowBlock,
    SnapshotAnswer,
    SnapshotBlock,
    SnapshotCompleteItem,
    SnapshotItemOutcome,
)

MAX_BLOCKS: Final = 2000
MAX_BLOCK_CHARS: Final = 4000
NO_SNAPSHOT: Final = "no_snapshot"
SNAPSHOT_CHANGED: Final = "snapshot changed"
HASH_DIFFERS: Final = "source hash differs from the stored translation"
NO_FIELDS: Final = "a translated page carries blocks and an engine"
NO_BLOCK: Final = "a translated page has at least one block"


class Settlement(enum.Enum):
    """What becomes of a refused item's task: a permanent failure, or a new task for the current artifact."""

    FAIL = "fail"
    REQUEUE = "requeue"


@dataclass(frozen=True, slots=True)
class Refusal:
    """Why an item is not stored, what the worker is told and what happens to the task."""

    outcome: SnapshotAnswer
    reason: str
    settlement: Settlement


@dataclass(frozen=True, slots=True)
class Facts:
    """What the checks read: the claimed task, the posted item, the latest snapshot and the stored index row."""

    task: SnapshotTranslationTask
    item: SnapshotCompleteItem
    latest: LatestSnapshot | None
    existing: SnapshotTranslation | None


def _rejected(reason: str) -> Refusal:
    return Refusal(SnapshotAnswer.REJECTED, reason, Settlement.FAIL)


def _part_problem(part: str) -> str | None:
    try:
        validate_i18n_value(part, max_len=MAX_BLOCK_CHARS)
    except ValueError as err:
        return str(err)
    return None


def _parts_problem(parts: Sequence[str]) -> str | None:
    if sum(len(part) for part in parts) > MAX_BLOCK_CHARS:
        return f"a block is over {MAX_BLOCK_CHARS} characters"
    return next((problem for part in parts if (problem := _part_problem(part))), None)


def _block_problem(block: SnapshotBlock) -> str | None:
    if isinstance(block, RowBlock):
        return _parts_problem(block.cells)
    if not block.text.strip():
        return "a text block is empty"
    return _parts_problem([block.text])


def blocks_problem(blocks: Sequence[SnapshotBlock]) -> str | None:
    """Return why ``blocks`` may not be stored, or ``None`` when they are within bounds."""
    if not blocks:
        return NO_BLOCK
    if len(blocks) > MAX_BLOCKS:
        return f"a page has more than {MAX_BLOCKS} blocks"
    problems = ((number, _block_problem(block)) for number, block in enumerate(blocks, start=1))
    return next((f"block {number}: {problem}" for number, problem in problems if problem), None)


def _translated(facts: Facts) -> Refusal | None:
    item = facts.item
    if item.outcome is not SnapshotItemOutcome.TRANSLATED:
        return None
    if item.blocks is None or item.engine is None:
        return _rejected(NO_FIELDS)
    problem = blocks_problem(item.blocks)
    return _rejected(problem) if problem else None


def _skipped(facts: Facts) -> Refusal | None:
    if facts.item.outcome is SnapshotItemOutcome.SKIPPED and facts.item.skipped_reason is None:
        return _rejected("a skipped page names its reason")
    return None


def _stale(facts: Facts) -> Refusal | None:
    if facts.latest is None:
        return Refusal(SnapshotAnswer.STALE, NO_SNAPSHOT, Settlement.FAIL)
    if facts.item.artifact_sha256 == facts.task.artifact_sha256 == facts.latest.sha256:
        return None
    return Refusal(SnapshotAnswer.STALE, SNAPSHOT_CHANGED, Settlement.REQUEUE)


def _unchanged(facts: Facts) -> Refusal | None:
    if facts.item.outcome is not SnapshotItemOutcome.UNCHANGED:
        return None
    if facts.existing is not None and facts.existing.source_hash == facts.item.source_hash:
        return None
    return _rejected(HASH_DIFFERS)


CHECKS: Final = (_translated, _skipped, _stale, _unchanged)
"""The checks in the order they run: the shape and bounds of the result, then staleness, then the unchanged hash."""


def first_refusal(facts: Facts) -> Refusal | None:
    """Return the refusal of the first check that fails, or ``None`` when the item may be stored."""
    return next((refusal for check in CHECKS if (refusal := check(facts))), None)
