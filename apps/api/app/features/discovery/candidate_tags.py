"""Tag suggestions of a candidate: the consensus of its mentions under the configured thresholds."""

from __future__ import annotations

from collections.abc import Iterable
from typing import NamedTuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import settings
from app.features.discovery.repository.candidate_completeness_tags import candidate_axis_support
from app.features.discovery.tags import TagAxis, TagSupport, axis_thresholds


class TagSuggestions(NamedTuple):
    """Support for every domain code and every life-situation code a candidate's mentions carry."""

    domains: list[TagSupport]
    situations: list[TagSupport]


def candidate_tag_suggestions(session: Session, candidate_id: UUID) -> TagSuggestions:
    """Return the domain and situation support of ``candidate_id``'s mentions, each under its own thresholds."""
    return TagSuggestions(
        candidate_axis_support(session, candidate_id, TagAxis.DOMAIN, axis_thresholds(settings, TagAxis.DOMAIN)),
        candidate_axis_support(session, candidate_id, TagAxis.SITUATION, axis_thresholds(settings, TagAxis.SITUATION)),
    )


def accepted_codes(supports: Iterable[TagSupport]) -> list[str]:
    """Return the codes that meet both thresholds."""
    return [support.code for support in supports if support.accepted]


def accepted_supports(supports: Iterable[TagSupport]) -> list[TagSupport]:
    """Return the supports that meet both thresholds, without collapsing them to bare codes."""
    return [support for support in supports if support.accepted]
