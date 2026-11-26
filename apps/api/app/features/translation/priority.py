"""Claim priority of translation tasks: higher confidence first, first translations before re-translations.

The queue hands out the lowest number first. The rank is the confidence in thousandths, inverted, so candidates with
close confidences are still told apart; the two bases keep every first translation ahead of every re-translation.
A procedure page has no confidence of its own: it ranks by the best candidate it mentions.

Priority includes a phase component: phase-1 items (breadth-first coverage) rank 0–99,999,
phase-2 items rank 100,000–199,999, and phase-3 items rank 200,000+. Within each phase,
confidence determines rank.
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
PHASE_BAND_WIDTH: Final = 100_000
"""Width of each phase band: phase 1 → 0–99,999, phase 2 → 100,000–199,999, phase 3 → 200,000+."""


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
    """Convert confidence [0.0, 1.0] to rank [0, 1000]."""
    return RANK_STEPS - round(min(max(confidence, 0.0), 1.0) * RANK_STEPS)


def _phase_band(phase: int) -> int:
    """Convert phase (1–3) to priority band offset."""
    return (phase - 1) * PHASE_BAND_WIDTH


def first_priority(confidence: float, phase: int = 1) -> int:
    """Return the priority of a candidate's first translation.

    Priority includes phase component: phase-1 items rank 0–99,999, phase-2 items
    rank 100,000–199,999, etc. Within phase, confidence determines rank.
    """
    return _phase_band(phase) + FIRST_BASE + _rank(confidence)


def retranslation_priority(confidence: float, phase: int = 1) -> int:
    """Return the priority of re-translating a stale translation.

    Priority includes phase component, same as first_priority.
    """
    return _phase_band(phase) + RETRANSLATION_BASE + _rank(confidence)


def upgrade_priority(phase: int = 1) -> int:
    """Return the priority of an Azure upgrade task.

    Upgrades rank behind all first and re-translations but respect phase ordering.
    """
    return _phase_band(phase) + UPGRADE_BASE


def page_confidence(confidences: Iterable[float]) -> float:
    """Return the confidence a procedure page ranks by: the highest of its candidates', ``0.0`` when it has none."""
    return max(confidences, default=0.0)


def snapshot_first_priority(confidences: Iterable[float], phase: int = 1) -> int:
    """Return the priority of a page's first translation, ranked by its best candidate and phase.

    Priority includes phase component: phase-1 items rank 0–99,999, phase-2 items
    rank 100,000–199,999, etc. Within phase, confidence determines rank.
    """
    return first_priority(page_confidence(confidences), phase=phase)


def snapshot_retranslation_priority(confidences: Iterable[float], phase: int = 1) -> int:
    """Return the priority of re-translating a page, ranked by its best candidate and phase.

    Priority includes phase component, same as snapshot_first_priority.
    """
    return retranslation_priority(page_confidence(confidences), phase=phase)
