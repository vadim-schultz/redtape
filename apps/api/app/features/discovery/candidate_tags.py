"""Tag suggestions of a candidate: the consensus of its mentions under the configured thresholds."""

from __future__ import annotations

from collections.abc import Iterable
from typing import NamedTuple

from app.config import settings
from app.features.discovery.tags import TagSupport, aggregate_tags
from app.models.discovery import DiscoveryCandidateMention


class TagSuggestions(NamedTuple):
    """Support for every domain code and every life-situation code a candidate's mentions carry."""

    domains: list[TagSupport]
    situations: list[TagSupport]


def candidate_tag_suggestions(mentions: Iterable[DiscoveryCandidateMention]) -> TagSuggestions:
    """Aggregate the codes of ``mentions`` with the thresholds from settings."""
    rows = list(mentions)
    thresholds = (settings.discovery_tag_min_procedures, settings.discovery_tag_min_share)
    return TagSuggestions(
        aggregate_tags([(m.catalogue_service_id, m.domain_codes) for m in rows], *thresholds),
        aggregate_tags([(m.catalogue_service_id, m.situation_codes) for m in rows], *thresholds),
    )


def accepted_codes(supports: Iterable[TagSupport]) -> list[str]:
    """Return the codes that meet both thresholds."""
    return [support.code for support in supports if support.accepted]
