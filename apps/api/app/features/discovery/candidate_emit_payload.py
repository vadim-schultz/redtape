"""Build the ``new_document`` payload of a document candidate."""

from __future__ import annotations

from typing import NamedTuple

from sqlalchemy.orm import Session

from app.features.discovery.candidate_tags import accepted_codes, candidate_tag_suggestions
from app.models.discovery import DiscoveryDocumentCandidate


class SuggestedTags(NamedTuple):
    """Domain and life-situation codes proposed for a candidate."""

    domain_codes: list[str]
    situation_codes: list[str]


def suggested_tags(session: Session, candidate: DiscoveryDocumentCandidate) -> SuggestedTags:
    """Return the codes its mentions agree on, or none while no code has enough support."""
    suggestions = candidate_tag_suggestions(session, candidate.id)
    return SuggestedTags(accepted_codes(suggestions.domains), accepted_codes(suggestions.situations))


def new_document_payload(candidate: DiscoveryDocumentCandidate, tags: SuggestedTags) -> dict[str, object]:
    """Return the payload of ``candidate`` with only the optional fields it has."""
    optional: dict[str, object] = {
        "official_url": candidate.official_url,
        "domain_codes": tags.domain_codes,
        "situation_codes": tags.situation_codes,
    }
    return {"title_i18n": candidate.title_i18n, **{name: value for name, value in optional.items() if value}}
