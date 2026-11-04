"""Build the ``new_document`` payload of a document candidate."""

from __future__ import annotations

from typing import NamedTuple

from sqlalchemy.orm import Session

from app.features.discovery.candidate_tags import candidate_tag_suggestions, usable_supports
from app.features.discovery.repository.candidate_leaf_codes import candidate_category_leaf_codes
from app.features.taxonomy.compatibility import LegacyTaxonomyAdapter
from app.models.discovery import DiscoveryDocumentCandidate


class SuggestedTags(NamedTuple):
    """Domain and life-situation codes proposed for a candidate, each with a confidence score.

    ``situation_leaf_codes`` keeps the raw leaf code of a situation code that a PVOG mention supplied
    (situation-tag-hierarchy chapter 3).
    """

    domain_codes: list[str]
    situation_codes: list[str]
    tag_confidence: dict[str, float] = {}
    situation_leaf_codes: dict[str, str] = {}
    category_codes: list[str] = []


def suggested_tags(session: Session, candidate: DiscoveryDocumentCandidate) -> SuggestedTags:
    """Return the codes that clear the inclusion floor, each tagged with its combined confidence score."""
    suggestions = candidate_tag_suggestions(session, candidate.id)
    category_supports = usable_supports(suggestions.categories)
    tag_confidence = {support.code: support.score for support in category_supports}
    category_codes = [support.code for support in category_supports]
    leaf_codes = candidate_category_leaf_codes(session, candidate.id)
    category_leaf_codes = {code: leaf_codes[code] for code in category_codes if code in leaf_codes}
    return SuggestedTags([], [], tag_confidence, category_leaf_codes, category_codes)


def new_document_payload(candidate: DiscoveryDocumentCandidate, tags: SuggestedTags) -> dict[str, object]:
    """Return the payload of ``candidate`` with only the optional fields it has."""
    category_codes, category_scores, pvog_leaf_codes = _canonical_tags(tags)
    optional: dict[str, object] = {
        "official_url": candidate.official_url,
        "category_codes": category_codes,
        "tag_confidence": category_scores,
        "pvog_leaf_codes": pvog_leaf_codes,
    }
    return {"title_i18n": candidate.title_i18n, **{name: value for name, value in optional.items() if value}}


def _canonical_tags(tags: SuggestedTags) -> tuple[list[str], dict[str, float], dict[str, str]]:
    """Translate compatibility tag objects to canonical category payload fields."""
    if tags.category_codes:
        return tags.category_codes, tags.tag_confidence, tags.situation_leaf_codes
    adapter = LegacyTaxonomyAdapter()
    translated = adapter.translate(domain_codes=tags.domain_codes, group_codes=(), situation_codes=tags.situation_codes)
    scores = adapter.canonical_scores(
        domain_scores={code: tags.tag_confidence[code] for code in tags.domain_codes if code in tags.tag_confidence},
        situation_scores={
            code: tags.tag_confidence[code] for code in tags.situation_codes if code in tags.tag_confidence
        },
    )
    leaf_codes = {
        target: leaf
        for source, leaf in tags.situation_leaf_codes.items()
        for target in adapter.translate(domain_codes=(), group_codes=(), situation_codes=(source,)).situation_targets
    }
    return list(dict.fromkeys((*translated.domain_targets, *translated.situation_targets))), scores, leaf_codes
