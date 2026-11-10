"""What each ``(candidate, locale)`` needs, decided from the current unit and the stored translation, with the counts."""

from __future__ import annotations

import enum
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from uuid import UUID

from app.features.translation.repository import IndexState
from app.features.translation.unit import TranslationUnit
from app.models.translation import TranslationSource


class Classification(enum.StrEnum):
    """What one ``(candidate, locale)`` needs."""

    MISSING = "missing"
    STALE = "stale"
    CURRENT = "current"
    HUMAN = "human_protected"
    NO_SOURCE = "no_source"


@dataclass(slots=True)
class EnqueueTotals:
    """Classifications of many ``(candidate, locale)`` slots, and how many tasks were queued or updated."""

    counts: Counter[Classification] = field(default_factory=Counter)
    enqueued: int = 0

    @property
    def missing(self) -> int:
        """Return the slots that have no translation yet."""
        return self.counts[Classification.MISSING]

    @property
    def stale(self) -> int:
        """Return the slots whose translation is of an older German unit."""
        return self.counts[Classification.STALE]

    @property
    def up_to_date(self) -> int:
        """Return the slots whose translation is current."""
        return self.counts[Classification.CURRENT]

    @property
    def human_protected(self) -> int:
        """Return the slots held by a human translation."""
        return self.counts[Classification.HUMAN]

    @property
    def no_source(self) -> int:
        """Return the slots of candidates without a German title."""
        return self.counts[Classification.NO_SOURCE]

    def merge(self, other: EnqueueTotals) -> None:
        """Add the counts of ``other``."""
        self.counts.update(other.counts)
        self.enqueued += other.enqueued


@dataclass(frozen=True, slots=True)
class Slot:
    """One ``(candidate, locale)`` and what it needs; ``source_hash`` is the current hash when there is a source."""

    candidate_id: UUID
    locale: str
    source_hash: str | None
    kind: Classification

    @property
    def key(self) -> tuple[UUID, str]:
        """Return the ``(candidate, locale)`` pair."""
        return (self.candidate_id, self.locale)


def classify(source_hash: str, row: IndexState | None) -> Classification:
    """Return what a translation unit at ``source_hash`` needs, given the index row of its locale."""
    if row is None:
        return Classification.MISSING
    if row.source is TranslationSource.HUMAN:
        return Classification.HUMAN
    return Classification.CURRENT if row.source_hash == source_hash else Classification.STALE


def _slot(candidate_id: UUID, locale: str, unit: TranslationUnit | None, row: IndexState | None) -> Slot:
    if unit is None:
        return Slot(candidate_id, locale, None, Classification.NO_SOURCE)
    return Slot(candidate_id, locale, unit.source_hash, classify(unit.source_hash, row))


def slots_for(
    candidate_ids: Sequence[UUID],
    locales: Sequence[str],
    units: Mapping[UUID, TranslationUnit],
    rows: Mapping[tuple[UUID, str], IndexState],
) -> list[Slot]:
    """Return one slot per candidate and locale, candidates in order, each classified against ``units`` and ``rows``."""
    return [
        _slot(candidate_id, locale, units.get(candidate_id), rows.get((candidate_id, locale)))
        for candidate_id in candidate_ids
        for locale in locales
    ]
