"""Claim priority of translation tasks: higher confidence first, first translations before re-translations.

The queue hands out the lowest number first. The rank is the confidence in thousandths, inverted, so candidates with
close confidences are still told apart; the two bases keep every first translation ahead of every re-translation.
"""

from __future__ import annotations

from typing import Final

RANK_STEPS: Final = 1000
"""Resolution of the confidence rank: a confidence of ``0.9`` ranks 100, of ``0.0`` ranks 1000."""
FIRST_BASE: Final = 0
RETRANSLATION_BASE: Final = 10_000
"""A stale translation still serves readers, so its refresh waits behind every untranslated candidate."""


def _rank(confidence: float) -> int:
    return RANK_STEPS - round(min(max(confidence, 0.0), 1.0) * RANK_STEPS)


def first_priority(confidence: float) -> int:
    """Return the priority of a candidate's first translation at ``confidence``."""
    return FIRST_BASE + _rank(confidence)


def retranslation_priority(confidence: float) -> int:
    """Return the priority of re-translating a stale translation at ``confidence``."""
    return RETRANSLATION_BASE + _rank(confidence)
