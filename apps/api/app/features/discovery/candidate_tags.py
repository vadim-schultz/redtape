"""Tag suggestions of a candidate: the score of its mentions, consensus combined via noisy-OR."""

from __future__ import annotations

from collections.abc import Iterable
from typing import NamedTuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.features.discovery.repository.candidate_axis_support import candidate_axis_support
from app.features.discovery.tags import MIN_SUGGESTED_SCORE, TagAxis, TagSupport
from app.features.taxonomy.compatibility import LegacyTaxonomyAdapter


class TagSuggestions(NamedTuple):
    """Support for compatibility axes and canonical categories a candidate's mentions carry."""

    domains: list[TagSupport]
    situations: list[TagSupport]
    categories: list[TagSupport]


def candidate_tag_suggestions(session: Session, candidate_id: UUID) -> TagSuggestions:
    """Return compatibility and canonical category support of ``candidate_id``'s mentions."""
    categories = canonical_category_supports(candidate_axis_support(session, candidate_id, TagAxis.CATEGORY))
    return TagSuggestions(
        candidate_axis_support(session, candidate_id, TagAxis.DOMAIN),
        candidate_axis_support(session, candidate_id, TagAxis.SITUATION),
        categories,
    )


def usable_codes(supports: Iterable[TagSupport]) -> list[str]:
    """Return the codes whose score clears the inclusion floor."""
    return [support.code for support in supports if support.score >= MIN_SUGGESTED_SCORE]


def usable_supports(supports: Iterable[TagSupport]) -> list[TagSupport]:
    """Return the supports whose score clears the inclusion floor, without collapsing them to bare codes."""
    return [support for support in supports if support.score >= MIN_SUGGESTED_SCORE]


def canonical_category_supports(supports: Iterable[TagSupport]) -> list[TagSupport]:
    """Translate compatibility-axis support to canonical category support using maximum scores."""
    adapter = LegacyTaxonomyAdapter()
    merged: dict[str, TagSupport] = {}
    for support in supports:
        targets = adapter.canonical_codes(
            domain_codes=(support.code,),
            situation_codes=(support.code,),
        )
        for code in targets:
            current = merged.get(code)
            if current is None or support.score > current.score:
                merged[code] = support._replace(code=code)
    return sorted(
        merged.values(),
        key=lambda support: (-support.procedures, support.code),
    )
