"""Build the ``new_document`` payload of a document candidate."""

from __future__ import annotations

from typing import NamedTuple

from app.models.discovery import DiscoveryDocumentCandidate


class SuggestedTags(NamedTuple):
    """Domain and life-situation codes proposed for a candidate."""

    domain_codes: list[str]
    situation_codes: list[str]


def suggested_tags(candidate: DiscoveryDocumentCandidate) -> SuggestedTags:
    """Return the codes to tag ``candidate`` with; none until the extraction suite aggregates its mentions' codes."""
    return SuggestedTags([], [])


def new_document_payload(candidate: DiscoveryDocumentCandidate, tags: SuggestedTags) -> dict[str, object]:
    """Return the payload of ``candidate`` with only the optional fields it has."""
    optional: dict[str, object] = {
        "official_url": candidate.official_url,
        "domain_codes": tags.domain_codes,
        "situation_codes": tags.situation_codes,
    }
    return {"title_i18n": candidate.title_i18n, **{name: value for name, value in optional.items() if value}}
