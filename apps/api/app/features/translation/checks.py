"""The ordered checks a posted translation passes before anything is written; the first refusal settles the item."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Final

from app.features.translation.text import InvalidTextError, clean
from app.models.translation import CandidateTranslation, TranslationSource, TranslationTask
from app.schema.translation.machine import TranslationCompleteItem, TranslationOutcome

HUMAN_EXISTS: Final = "human_exists"
SOURCE_CHANGED: Final = "german source changed"


class Settlement(enum.Enum):
    """What becomes of the task when its item is refused."""

    FAIL = "fail"
    COMPLETE = "complete"
    REQUEUE = "requeue"


@dataclass(frozen=True, slots=True)
class Refusal:
    """Why an item is not stored, what the worker is told and what happens to the task."""

    outcome: TranslationOutcome
    reason: str
    settlement: Settlement


@dataclass(frozen=True, slots=True)
class Facts:
    """What the checks read: the claimed task, the posted item, the current source hash and the stored row."""

    task: TranslationTask
    item: TranslationCompleteItem
    current_hash: str | None
    existing: CandidateTranslation | None


def _bounds(facts: Facts) -> Refusal | None:
    try:
        clean(facts.item)
    except InvalidTextError as err:
        return Refusal(TranslationOutcome.REJECTED, str(err), Settlement.FAIL)
    return None


def _stale(facts: Facts) -> Refusal | None:
    leased_for = facts.task.source_hash
    if facts.item.source_hash == leased_for == facts.current_hash:
        return None
    return Refusal(TranslationOutcome.STALE, SOURCE_CHANGED, Settlement.REQUEUE)


def _human(facts: Facts) -> Refusal | None:
    if facts.existing is None or facts.existing.source is not TranslationSource.HUMAN:
        return None
    return Refusal(TranslationOutcome.REJECTED, HUMAN_EXISTS, Settlement.COMPLETE)


CHECKS: Final = (_bounds, _stale, _human)
"""The checks in the order they run: text bounds, then staleness, then the human-translation guard."""


def first_refusal(facts: Facts) -> Refusal | None:
    """Return the refusal of the first check that fails, or ``None`` when the item may be stored."""
    return next((refusal for check in CHECKS if (refusal := check(facts))), None)
