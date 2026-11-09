"""Category suggestions of a candidate: the score of its mentions, consensus combined via noisy-OR."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy.orm import Session

from app.features.discovery.repository.candidate_category_support import candidate_category_support
from app.features.discovery.tags import MIN_SUGGESTED_SCORE, TagSupport


def candidate_category_suggestions(session: Session, candidate_id: UUID) -> list[TagSupport]:
    """Return the canonical category support of ``candidate_id``'s mentions, most supported first."""
    return candidate_category_support(session, candidate_id)


def usable_codes(supports: Iterable[TagSupport]) -> list[str]:
    """Return the codes whose score clears the inclusion floor."""
    return [support.code for support in usable_supports(supports)]


def usable_supports(supports: Iterable[TagSupport]) -> list[TagSupport]:
    """Return the supports whose score clears the inclusion floor, without collapsing them to bare codes."""
    return [support for support in supports if support.score >= MIN_SUGGESTED_SCORE]
