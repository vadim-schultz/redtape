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
    """A compatibility axis or the canonical category collection of a mention."""

    DOMAIN = "domain"
    SITUATION = "situation"
    CATEGORY = "category"

    @property
    def column(self) -> InstrumentedAttribute[list[str] | None]:
        """Return the mention column holding this axis' codes."""
        if self is TagAxis.SITUATION:
            return Mention.situation_codes
        return Mention.domain_codes

    @property
    def confidence_column(self) -> InstrumentedAttribute[float | None]:
        """Return the mention column holding this axis' direct-source confidence, when it supplies one.

        ``NULL`` means the mention's assertion is LLM-extracted — score it via :func:`llm_evidence_score`;
        a non-``NULL`` value means the mention supplies its own fixed confidence directly (a PVOG leaf today,
        a vote-backed estimate in future), independent of how many other procedures agree.
        """
        if self is TagAxis.SITUATION:
            return Mention.direct_situation_confidence
        return Mention.direct_domain_confidence


def llm_evidence_score(procedures: int, share: float) -> float:
    """Return a saturating LLM-only corroboration score, anchored to situation-tag-activation's LR1 sample.

    One procedure lands near its measured 37.5-62.5% midpoint; two or more approach the historical
    "high" ceiling. Not yet validated beyond that sample (see gaps-and-decisions.md P1).
    """
    if procedures <= 0:
        return 0.0
    return min(LLM_SCORE_CEILING, LLM_SCORE_BASE + LLM_SCORE_STEP * (procedures - 1)) * share


def noisy_or(scores: Iterable[float]) -> float:
    """Combine independent evidence as ``1 - product(1 - s)``.

    A ``0.0`` term (no evidence) is the identity, so the LLM score can always be passed even when a code
    has zero LLM-extracted mentions.
    """
    remaining = 1.0
    for score in scores:
        remaining *= 1 - score
    return 1 - remaining
