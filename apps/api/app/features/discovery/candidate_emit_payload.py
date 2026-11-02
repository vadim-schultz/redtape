"""Build the ``new_document`` payload of a document candidate."""

from __future__ import annotations

from typing import NamedTuple

from sqlalchemy.orm import Session

from app.features.discovery.candidate_tags import candidate_tag_suggestions, usable_codes, usable_supports
from app.features.discovery.repository.candidate_leaf_codes import candidate_situation_leaf_codes
from app.models.discovery import DiscoveryDocumentCandidate


class SuggestedTags(NamedTuple):
    """Domain and life-situation codes proposed for a candidate, with a confidence score per usable code
    and, for a situation code a PVOG mention supplied, its raw leaf code (situation-tag-hierarchy chapter 3)."""

    domain_codes: list[str]
    situation_codes: list[str]
    tag_confidence: dict[str, float] = {}
    situation_leaf_codes: dict[str, str] = {}


def suggested_tags(session: Session, candidate: DiscoveryDocumentCandidate) -> SuggestedTags:
    """Return the codes that clear the inclusion floor, each tagged with its combined confidence score."""
    suggestions = candidate_tag_suggestions(session, candidate.id)
    domain_supports = usable_supports(suggestions.domains)
    situation_supports = usable_supports(suggestions.situations)
    tag_confidence = {support.code: support.score for support in (*domain_supports, *situation_supports)}
    situation_codes = usable_codes(suggestions.situations)
    leaf_codes = candidate_situation_leaf_codes(session, candidate.id)
    situation_leaf_codes = {code: leaf_codes[code] for code in situation_codes if code in leaf_codes}
    return SuggestedTags(usable_codes(suggestions.domains), situation_codes, tag_confidence, situation_leaf_codes)


def new_document_payload(candidate: DiscoveryDocumentCandidate, tags: SuggestedTags) -> dict[str, object]:
    """Return the payload of ``candidate`` with only the optional fields it has."""
    optional: dict[str, object] = {
        "official_url": candidate.official_url,
        "domain_codes": tags.domain_codes,
        "situation_codes": tags.situation_codes,
        "tag_confidence": tags.tag_confidence,
        "situation_leaf_codes": tags.situation_leaf_codes,
    }
    return {"title_i18n": candidate.title_i18n, **{name: value for name, value in optional.items() if value}}
