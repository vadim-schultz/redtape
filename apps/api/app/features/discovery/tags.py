"""Tag consensus vocabulary: the shared types the merged SQL engine computes support against.

Chapter 1 of ``situation-tag-hierarchy`` replaces every accept/reject boolean with a continuous
``[0, 1]`` score: a direct-source confidence (manual stays a full override; PVOG and any future
direct source combine via :func:`noisy_or`) and a calibrated LLM-evidence curve (:func:`llm_evidence_score`).
"""

from __future__ import annotations

import enum
from collections.abc import Iterable
from typing import NamedTuple

from sqlalchemy.orm import InstrumentedAttribute

from app.models.discovery import DiscoveryCandidateMention as Mention

MANUAL_EXTRACTOR = "manual"
"""The ``extractor`` of a mention written by a curator; its codes are authoritative for their axis."""

MIN_SUGGESTED_SCORE = 0.05
"""Below this, a code isn't offered at all — noise suppression, not a precision claim (D9)."""

LLM_SCORE_BASE = 0.5
LLM_SCORE_STEP = 0.35
LLM_SCORE_CEILING = 0.95


class TagSupport(NamedTuple):
    """How many procedures carry one code, their share of the tagged procedures, and its combined score."""

    code: str
    procedures: int
    share: float
    score: float


class TagAxis(enum.Enum):
    """A tag axis of a mention: the array column of codes and the column of direct-source confidence."""

    DOMAIN = "domain"
    SITUATION = "situation"

    @property
    def column(self) -> InstrumentedAttribute[list[str] | None]:
        """Return the mention column holding this axis' codes."""
        return Mention.domain_codes if self is TagAxis.DOMAIN else Mention.situation_codes

    @property
    def confidence_column(self) -> InstrumentedAttribute[float | None]:
        """Return the mention column holding this axis' direct-source confidence, when it supplies one.

        ``NULL`` means the mention's assertion is LLM-extracted — score it via :func:`llm_evidence_score`;
        a non-``NULL`` value means the mention supplies its own fixed confidence directly (a PVOG leaf today,
        a vote-backed estimate in future), independent of how many other procedures agree.
        """
        return Mention.direct_domain_confidence if self is TagAxis.DOMAIN else Mention.direct_situation_confidence


def llm_evidence_score(procedures: int, share: float) -> float:
    """Saturating curve for LLM-only corroboration, anchored to situation-tag-activation's LR1 sample:
    one procedure lands near its measured 37.5-62.5% midpoint, two or more approach the historical
    "high" ceiling. Not yet validated beyond that sample — see gaps-and-decisions.md P1.
    """
    if procedures <= 0:
        return 0.0
    return min(LLM_SCORE_CEILING, LLM_SCORE_BASE + LLM_SCORE_STEP * (procedures - 1)) * share


def noisy_or(scores: Iterable[float]) -> float:
    """Combine independent evidence: ``1 - product(1 - s)``. A ``0.0`` term (no evidence) is the identity —
    safe to always pass the LLM score even when there were zero LLM-extracted mentions for a code.
    """
    remaining = 1.0
    for score in scores:
        remaining *= 1 - score
    return 1 - remaining
