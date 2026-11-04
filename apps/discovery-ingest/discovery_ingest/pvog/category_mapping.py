"""Load the frozen PVOG-to-category mapping and create source-backed evidence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, TypeAdapter

from discovery_ingest.pvog.models import PvogSourcePath

_ARTIFACT_PATH = (
    Path(__file__).resolve().parents[4] / ".plans" / "category-taxonomy-migration" / "category-contract-v1.json"
)
CategoryEvidenceState = Literal["mapped", "review"]


@dataclass(frozen=True, slots=True)
class PvogCategoryEvidence:
    """Canonical category evidence with the PVOG leaf and source path that support it."""

    leaf_code: str
    category_codes: tuple[str, ...]
    confidence: float
    state: CategoryEvidenceState
    reason: str
    mapping_version: str
    source_path: PvogSourcePath


class _CategoryPayload(BaseModel):
    code: str
    is_active: bool = True
    source_parent_codes: tuple[str, ...] = ()


class _LeafMappingPayload(BaseModel):
    leaf_code: str
    category_codes: tuple[str, ...]
    confidence: float = Field(ge=0, le=1)
    state: CategoryEvidenceState
    reason: str


class _ContractPayload(BaseModel):
    artifact_version: str
    pvog_source_version: str
    categories: tuple[_CategoryPayload, ...]
    legacy_crosswalk: tuple[_LegacyMappingPayload, ...] = ()
    pvog_leaf_mappings: tuple[_LeafMappingPayload, ...]


class _LegacyMappingPayload(BaseModel):
    axis: Literal["domain", "life_situation"]
    source_code: str
    state: Literal["mapped", "unmapped", "manual-review"]
    target_codes: tuple[str, ...] = ()


def _load_category_mappings() -> tuple[
    str,
    str,
    dict[str, _LeafMappingPayload],
    dict[str, tuple[str, ...]],
    dict[tuple[str, str], tuple[str, ...]],
]:
    """Load the canonical leaf mappings and reject unknown or duplicate targets."""
    payload = TypeAdapter(_ContractPayload).validate_json(_ARTIFACT_PATH.read_bytes())
    active_categories = {category.code for category in payload.categories if category.is_active}
    category_parents = {category.code: category.source_parent_codes for category in payload.categories}
    mappings: dict[str, _LeafMappingPayload] = {}
    for mapping in payload.pvog_leaf_mappings:
        if not mapping.category_codes:
            raise ValueError(f"PVOG mapping has no category target for {mapping.leaf_code}")
        if len(set(mapping.category_codes)) != len(mapping.category_codes):
            raise ValueError(f"PVOG mapping has duplicate category target for {mapping.leaf_code}")
        if any(code not in active_categories for code in mapping.category_codes):
            raise ValueError(f"PVOG mapping has unknown category target for {mapping.leaf_code}")
        if mapping.leaf_code in mappings:
            raise ValueError(f"PVOG mapping has duplicate leaf {mapping.leaf_code}")
        if not mapping.reason.strip():
            raise ValueError(f"PVOG mapping has no reason for {mapping.leaf_code}")
        mappings[mapping.leaf_code] = mapping
    legacy: dict[tuple[str, str], tuple[str, ...]] = {}
    for legacy_mapping in payload.legacy_crosswalk:
        if legacy_mapping.state == "mapped":
            if any(code not in active_categories for code in legacy_mapping.target_codes):
                raise ValueError(f"legacy mapping has unknown category target for {legacy_mapping.source_code}")
            legacy[(legacy_mapping.axis, legacy_mapping.source_code)] = legacy_mapping.target_codes
    return payload.artifact_version, payload.pvog_source_version, mappings, category_parents, legacy


(
    PVOG_CATEGORY_MAPPING_VERSION,
    PVOG_SOURCE_VERSION,
    _PVOG_CATEGORY_MAPPINGS,
    _CATEGORY_SOURCE_PARENTS,
    _LEGACY_CATEGORY_MAPPINGS,
) = _load_category_mappings()
PERSONAL_MATTER_TO_CATEGORY: dict[str, tuple[str, ...]] = {
    leaf_code: mapping.category_codes for leaf_code, mapping in _PVOG_CATEGORY_MAPPINGS.items()
}
PERSONAL_MATTER_CATEGORY_CONFIDENCE: dict[str, float] = {
    leaf_code: mapping.confidence for leaf_code, mapping in _PVOG_CATEGORY_MAPPINGS.items()
}


def category_evidence_for_path(path: PvogSourcePath) -> PvogCategoryEvidence | None:
    """Map a complete PVOG path to canonical evidence; never infer a category from a bare leaf."""
    if not path.has_parent_path or path.leaf_code is None:
        return None
    mapping = _PVOG_CATEGORY_MAPPINGS.get(path.leaf_code)
    if mapping is None:
        return None
    if not any(path.parent_code in _CATEGORY_SOURCE_PARENTS[code] for code in mapping.category_codes):
        return None
    return PvogCategoryEvidence(
        leaf_code=path.leaf_code,
        category_codes=mapping.category_codes,
        confidence=mapping.confidence,
        state=mapping.state,
        reason=mapping.reason,
        mapping_version=PVOG_CATEGORY_MAPPING_VERSION,
        source_path=path,
    )


def categories_for_legacy_codes(axis: Literal["domain", "life_situation"], codes: tuple[str, ...]) -> tuple[str, ...]:
    """Translate compatibility-axis codes through the frozen crosswalk."""
    return tuple(
        dict.fromkeys(category for code in codes for category in _LEGACY_CATEGORY_MAPPINGS.get((axis, code), ()))
    )


__all__ = [
    "CategoryEvidenceState",
    "PERSONAL_MATTER_CATEGORY_CONFIDENCE",
    "PERSONAL_MATTER_TO_CATEGORY",
    "PVOG_CATEGORY_MAPPING_VERSION",
    "PVOG_SOURCE_VERSION",
    "PvogCategoryEvidence",
    "categories_for_legacy_codes",
    "category_evidence_for_path",
]
