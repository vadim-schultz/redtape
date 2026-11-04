"""Build and refresh mention rows from validated batch items."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast
from uuid import UUID

from app.features.discovery.candidate_codes import ItemCodes
from app.models.discovery import DiscoveryCandidateMention, DiscoveryDocumentCandidate, PvogSourcePathData
from app.schema.discovery.candidates import CandidateMentionItem


@dataclass(frozen=True, slots=True)
class PreparedMention:
    """An item with the key, jurisdiction and vocabulary-checked codes resolved before any write."""

    item: CandidateMentionItem
    key: str
    jurisdiction_id: UUID
    codes: ItemCodes


def new_mention(candidate: DiscoveryDocumentCandidate, prepared: PreparedMention) -> DiscoveryCandidateMention:
    """Return an unsaved mention of ``candidate`` for ``prepared``."""
    item = prepared.item
    mention = DiscoveryCandidateMention(
        candidate_id=candidate.id,
        catalogue_service_id=item.catalogue_service_id,
        role=item.role,
        source_field=item.source_field,
        excerpt=item.excerpt,
        artifact_id=item.artifact_id,
        extractor=item.extractor,
        extractor_version=item.extractor_version,
    )
    _apply_conditions(mention, prepared)
    return mention


def refresh_mention(mention: DiscoveryCandidateMention, prepared: PreparedMention) -> None:
    """Overwrite what a re-run may change; the artifact is kept when the item names none."""
    item = prepared.item
    mention.excerpt = item.excerpt
    mention.extractor = item.extractor
    mention.extractor_version = item.extractor_version
    mention.artifact_id = item.artifact_id or mention.artifact_id
    _apply_conditions(mention, prepared)
    mention.category_codes = prepared.codes.category_codes
    mention.direct_category_confidence = prepared.item.direct_category_confidence


def _apply_conditions(mention: DiscoveryCandidateMention, prepared: PreparedMention) -> None:
    mention.condition = prepared.item.condition
    mention.is_optional = prepared.item.is_optional
    mention.category_codes = prepared.codes.category_codes
    mention.direct_category_confidence = prepared.item.direct_category_confidence
    mention.pvog_leaf_code = prepared.item.pvog_leaf_code
    path = prepared.item.pvog_source_path
    mention.pvog_source_path = None if path is None else cast(PvogSourcePathData, path.model_dump(exclude_none=True))
    mention.pvog_mapping_version = prepared.item.pvog_mapping_version
