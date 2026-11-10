"""Typed outcomes of refreshing search text."""

from __future__ import annotations

import enum
from collections import Counter
from dataclasses import dataclass, field


class RefreshStatus(enum.StrEnum):
    """What a refresh did to the search-text row."""

    WRITTEN = "written"
    UNCHANGED = "unchanged"
    SKIPPED_EMPTY = "skipped_empty"


@dataclass(frozen=True, slots=True)
class RefreshResult:
    """The status of one refresh and whether it queued embedding work."""

    status: RefreshStatus
    enqueued: bool = False


@dataclass(slots=True)
class RefreshTotals:
    """Outcomes of many refreshes, summed."""

    counts: Counter[RefreshStatus] = field(default_factory=Counter)
    enqueued: int = 0

    @property
    def written(self) -> int:
        """Return the rows written."""
        return self.counts[RefreshStatus.WRITTEN]

    @property
    def unchanged(self) -> int:
        """Return the rows whose hash was already current."""
        return self.counts[RefreshStatus.UNCHANGED]

    @property
    def skipped_empty(self) -> int:
        """Return the candidates that had no usable text."""
        return self.counts[RefreshStatus.SKIPPED_EMPTY]

    def add(self, result: RefreshResult) -> None:
        """Count ``result``."""
        self.counts[result.status] += 1
        self.enqueued += result.enqueued

    def merge(self, other: RefreshTotals) -> None:
        """Add the counts of ``other``."""
        self.counts.update(other.counts)
        self.enqueued += other.enqueued
