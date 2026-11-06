"""Map the category contract onto the machine vocabulary: the PVOG leaf crosswalk and the legacy crosswalk."""

from __future__ import annotations

from app.schema.taxonomy.read import (
    CrosswalkRead,
    LegacyMappingRead,
    PvogLeafMappingRead,
    VocabularyResponse,
    VocabularyTerm,
)
from app.shared.taxonomy.category_types import CategoryDefinition, LegacyMapping, PvogLeafMapping
from app.shared.taxonomy.contract_loader import CategoryContract


def crosswalk_read(contract: CategoryContract) -> CrosswalkRead:
    """Return the PVOG leaf crosswalk and the legacy crosswalk of ``contract`` with their versions."""
    return CrosswalkRead(
        artifact_version=contract.artifact_version,
        pvog_source_version=contract.pvog_source_version,
        pvog_leaf_mappings=[_leaf_read(mapping) for mapping in contract.pvog_leaf_mappings],
        legacy_crosswalk=[_legacy_read(mapping) for mapping in contract.legacy_crosswalk],
    )


def contract_vocabulary(contract: CategoryContract) -> VocabularyResponse:
    """Return the vocabulary the artifact yields by itself: its active terms and its crosswalk, without database rows."""
    return VocabularyResponse(
        categories=[_term_read(category) for category in contract.categories if category.is_active],
        crosswalk=crosswalk_read(contract),
    )


def _leaf_read(mapping: PvogLeafMapping) -> PvogLeafMappingRead:
    """Map one PVOG leaf mapping onto its read model."""
    return PvogLeafMappingRead(
        leaf_code=mapping.leaf_code,
        category_codes=list(mapping.category_codes),
        confidence=mapping.confidence,
        state=mapping.state,
        reason=mapping.reason,
    )


def _legacy_read(mapping: LegacyMapping) -> LegacyMappingRead:
    """Map one legacy disposition onto its read model."""
    return LegacyMappingRead(
        axis=mapping.axis,
        source_code=mapping.source_code,
        state=mapping.state,
        target_codes=list(mapping.target_codes),
        reason=mapping.reason,
        score_combination=mapping.score_combination,
    )


def _term_read(category: CategoryDefinition) -> VocabularyTerm:
    """Map one active artifact category onto the vocabulary term the route serves."""
    return VocabularyTerm(
        code=category.code,
        parent_code=category.parent_code,
        name_i18n=dict(category.name_i18n),
        description_i18n=dict(category.description_i18n),
        icon=category.icon,
        source_parent_codes=sorted(category.source_parent_codes),
    )
