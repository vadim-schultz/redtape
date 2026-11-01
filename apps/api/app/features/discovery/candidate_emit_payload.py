"""Build the ``new_document`` payload of a document candidate."""

from __future__ import annotations

from typing import Literal, NamedTuple

from sqlalchemy.orm import Session

from app.features.discovery.candidate_tags import accepted_codes, accepted_supports, candidate_tag_suggestions
from app.features.discovery.tags import confidence_tier
from app.models.discovery import DiscoveryDocumentCandidate


class SuggestedTags(NamedTuple):
    """Domain and life-situation codes proposed for a candidate, with a confidence tier per accepted code."""

    domain_codes: list[str]
    situation_codes: list[str]
    tag_confidence: dict[str, Literal["high", "low"]] = {}


def suggested_tags(session: Session, candidate: DiscoveryDocumentCandidate) -> SuggestedTags:
    """Return the codes its mentions agree on, each tagged with its confidence tier (decision D5)."""
    suggestions = candidate_tag_suggestions(session, candidate.id)
    domain_supports = accepted_supports(suggestions.domains)
    situation_supports = accepted_supports(suggestions.situations)
    tag_confidence = {support.code: confidence_tier(support) for support in (*domain_supports, *situation_supports)}
    return SuggestedTags(accepted_codes(suggestions.domains), accepted_codes(suggestions.situations), tag_confidence)


def new_document_payload(candidate: DiscoveryDocumentCandidate, tags: SuggestedTags) -> dict[str, object]:
    """Return the payload of ``candidate`` with only the optional fields it has."""
    optional: dict[str, object] = {
        "official_url": candidate.official_url,
        "domain_codes": tags.domain_codes,
        "situation_codes": tags.situation_codes,
        "tag_confidence": tags.tag_confidence,
    }
    return {"title_i18n": candidate.title_i18n, **{name: value for name, value in optional.items() if value}}
