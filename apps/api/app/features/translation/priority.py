"""Claim priority of translation tasks: higher confidence first, first translations before re-translations.

The queue hands out the lowest number first. The rank is the confidence in thousandths, inverted, so candidates with
close confidences are still told apart; the two bases keep every first translation ahead of every re-translation.
A procedure page has no confidence of its own: it ranks by the best candidate it mentions.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final

RANK_STEPS: Final = 1000
"""Resolution of the confidence rank: a confidence of ``0.9`` ranks 100, of ``0.0`` ranks 1000."""
FIRST_BASE: Final = 0
FIRST_CEILING: Final = FIRST_BASE + RANK_STEPS
"""The lowest-ranked first translation (confidence ``0.0``): the top of the first-translation band."""
RETRANSLATION_BASE: Final = 10_000
"""A stale translation still serves readers, so its refresh waits behind every untranslated candidate."""
UPGRADE_BASE: Final = 20_000
"""An Azure upgrade of a tail row waits behind every first and re-translation, so it runs on idle Azure capacity."""


@dataclass(frozen=True, slots=True)
class PriorityRange:
    """An inclusive band of claim priorities; a ``None`` maximum leaves the band open above."""

    minimum: int = 0
    maximum: int | None = None

    def __post_init__(self) -> None:
        """Refuse a band whose maximum is below its minimum."""
        if self.maximum is not None and self.maximum < self.minimum:
            raise ValueError(f"priority range {self.minimum}..{self.maximum} is inverted")


def _rank(confidence: float) -> int:
    return RANK_STEPS - round(min(max(confidence, 0.0), 1.0) * RANK_STEPS)


def first_priority(confidence: float) -> int:
    """Return the priority of a candidate's first translation at ``confidence``."""
    return FIRST_BASE + _rank(confidence)


def retranslation_priority(confidence: float) -> int:
    """Return the priority of re-translating a stale translation at ``confidence``."""
    return RETRANSLATION_BASE + _rank(confidence)


def page_confidence(confidences: Iterable[float]) -> float:
    """Return the confidence a procedure page ranks by: the highest of its candidates', ``0.0`` when it has none."""
    return max(confidences, default=0.0)


def snapshot_first_priority(confidences: Iterable[float]) -> int:
    """Return the priority of a page's first translation, ranked by its best candidate."""
    return first_priority(page_confidence(confidences))


def snapshot_retranslation_priority(confidences: Iterable[float]) -> int:
    """Return the priority of re-translating a page, ranked by its best candidate."""
    return retranslation_priority(page_confidence(confidences))
