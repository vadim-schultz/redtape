"""Tag suggestions of a candidate: the score of its mentions, consensus combined via noisy-OR."""

from __future__ import annotations

from collections.abc import Iterable
from typing import NamedTuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.features.discovery.repository.candidate_axis_support import candidate_axis_support
from app.features.discovery.tags import MIN_SUGGESTED_SCORE, TagAxis, TagSupport


class TagSuggestions(NamedTuple):
    """Support for every domain code and every life-situation code a candidate's mentions carry."""

    domains: list[TagSupport]
    situations: list[TagSupport]


def candidate_tag_suggestions(session: Session, candidate_id: UUID) -> TagSuggestions:
    """Return the domain and situation support of ``candidate_id``'s mentions."""
    return TagSuggestions(
        candidate_axis_support(session, candidate_id, TagAxis.DOMAIN),
        candidate_axis_support(session, candidate_id, TagAxis.SITUATION),
    )


def usable_codes(supports: Iterable[TagSupport]) -> list[str]:
    """Return the codes whose score clears the inclusion floor."""
    return [support.code for support in supports if support.score >= MIN_SUGGESTED_SCORE]


def usable_supports(supports: Iterable[TagSupport]) -> list[TagSupport]:
    """Return the supports whose score clears the inclusion floor, without collapsing them to bare codes."""
    return [support for support in supports if support.score >= MIN_SUGGESTED_SCORE]
