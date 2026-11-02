"""Build the ``new_document`` payload of a document candidate."""

from __future__ import annotations

from typing import NamedTuple

from sqlalchemy.orm import Session

from app.features.discovery.candidate_tags import candidate_tag_suggestions, usable_codes, usable_supports
from app.models.discovery import DiscoveryDocumentCandidate


class SuggestedTags(NamedTuple):
    """Domain and life-situation codes proposed for a candidate, with a confidence score per usable code."""

    domain_codes: list[str]
    situation_codes: list[str]
    tag_confidence: dict[str, float] = {}


def suggested_tags(session: Session, candidate: DiscoveryDocumentCandidate) -> SuggestedTags:
    """Return the codes that clear the inclusion floor, each tagged with its combined confidence score."""
    suggestions = candidate_tag_suggestions(session, candidate.id)
    domain_supports = usable_supports(suggestions.domains)
    situation_supports = usable_supports(suggestions.situations)
    tag_confidence = {support.code: support.score for support in (*domain_supports, *situation_supports)}
    return SuggestedTags(usable_codes(suggestions.domains), usable_codes(suggestions.situations), tag_confidence)


def new_document_payload(candidate: DiscoveryDocumentCandidate, tags: SuggestedTags) -> dict[str, object]:
    """Return the payload of ``candidate`` with only the optional fields it has."""
    optional: dict[str, object] = {
        "official_url": candidate.official_url,
        "domain_codes": tags.domain_codes,
        "situation_codes": tags.situation_codes,
        "tag_confidence": tags.tag_confidence,
    }
    return {"title_i18n": candidate.title_i18n, **{name: value for name, value in optional.items() if value}}
