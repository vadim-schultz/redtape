"""Tag suggestions of a candidate: the consensus of its mentions under the configured thresholds."""

from __future__ import annotations

from collections.abc import Iterable
from typing import NamedTuple

from app.config import settings
from app.features.discovery.tags import ProvenancedMention, TagSupport, aggregate_tags, curated_codes
from app.models.discovery import DiscoveryCandidateMention


class TagSuggestions(NamedTuple):
    """Support for every domain code and every life-situation code a candidate's mentions carry."""

    domains: list[TagSupport]
    situations: list[TagSupport]


def _consensus(mentions: list[ProvenancedMention]) -> list[TagSupport]:
    tagged = [(procedure, codes) for procedure, _extractor, codes in mentions]
    return aggregate_tags(tagged, settings.discovery_tag_min_procedures, settings.discovery_tag_min_share)


def _axis_support(mentions: list[ProvenancedMention]) -> list[TagSupport]:
    """Return the curated codes of one axis, else its consensus under the configured thresholds."""
    return curated_codes(mentions) or _consensus(mentions)


def candidate_tag_suggestions(mentions: Iterable[DiscoveryCandidateMention]) -> TagSuggestions:
    """Aggregate the codes of ``mentions``; a manual mention replaces the consensus of its axis."""
    rows = list(mentions)
    return TagSuggestions(
        _axis_support([(m.catalogue_service_id, m.extractor, m.domain_codes) for m in rows]),
        _axis_support([(m.catalogue_service_id, m.extractor, m.situation_codes) for m in rows]),
    )


def accepted_codes(supports: Iterable[TagSupport]) -> list[str]:
    """Return the codes that meet both thresholds."""
    return [support.code for support in supports if support.accepted]
