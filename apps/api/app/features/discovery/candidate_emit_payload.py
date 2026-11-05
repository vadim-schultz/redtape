"""Build the ``new_document`` payload of a document candidate."""

from __future__ import annotations

from typing import NamedTuple

from sqlalchemy.orm import Session

from app.features.discovery.candidate_tags import candidate_category_suggestions, usable_supports
from app.features.discovery.repository.candidate_leaf_codes import candidate_category_leaf_codes
from app.models.discovery import DiscoveryDocumentCandidate


class SuggestedTags(NamedTuple):
    """Canonical category codes proposed for a candidate, each with its combined confidence and PVOG leaf."""

    category_codes: list[str]
    tag_confidence: dict[str, float]
    pvog_leaf_codes: dict[str, str]


def suggested_tags(session: Session, candidate: DiscoveryDocumentCandidate) -> SuggestedTags:
    """Return the category codes that clear the inclusion floor, each with its score and its PVOG leaf if any."""
    supports = usable_supports(candidate_category_suggestions(session, candidate.id))
    leaf_codes = candidate_category_leaf_codes(session, candidate.id)
    codes = [support.code for support in supports]
    return SuggestedTags(
        category_codes=codes,
        tag_confidence={support.code: support.score for support in supports},
        pvog_leaf_codes={code: leaf_codes[code] for code in codes if code in leaf_codes},
    )


def new_document_payload(candidate: DiscoveryDocumentCandidate, tags: SuggestedTags) -> dict[str, object]:
    """Return the payload of ``candidate`` with only the optional fields it has."""
    optional: dict[str, object] = {
        "official_url": candidate.official_url,
        "category_codes": tags.category_codes,
        "tag_confidence": tags.tag_confidence,
        "pvog_leaf_codes": tags.pvog_leaf_codes,
    }
    return {"title_i18n": candidate.title_i18n, **{name: value for name, value in optional.items() if value}}
