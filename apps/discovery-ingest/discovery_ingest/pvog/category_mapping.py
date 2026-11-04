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


class _LeafMappingPayload(BaseModel):
    leaf_code: str
    category_codes: tuple[str, ...]
    confidence: float = Field(ge=0, le=1)
    state: CategoryEvidenceState
    reason: str


class _ContractPayload(BaseModel):
    artifact_version: str
    categories: tuple[_CategoryPayload, ...]
    pvog_leaf_mappings: tuple[_LeafMappingPayload, ...]


def _load_category_mappings() -> tuple[str, dict[str, _LeafMappingPayload]]:
    """Load the canonical leaf mappings and reject unknown or duplicate targets."""
    payload = TypeAdapter(_ContractPayload).validate_json(_ARTIFACT_PATH.read_bytes())
    category_codes = {category.code for category in payload.categories}
    mappings: dict[str, _LeafMappingPayload] = {}
    for mapping in payload.pvog_leaf_mappings:
        if not mapping.category_codes:
            raise ValueError(f"PVOG mapping has no category target for {mapping.leaf_code}")
        if len(set(mapping.category_codes)) != len(mapping.category_codes):
            raise ValueError(f"PVOG mapping has duplicate category target for {mapping.leaf_code}")
        if any(code not in category_codes for code in mapping.category_codes):
            raise ValueError(f"PVOG mapping has unknown category target for {mapping.leaf_code}")
        if mapping.leaf_code in mappings:
            raise ValueError(f"PVOG mapping has duplicate leaf {mapping.leaf_code}")
        if not mapping.reason.strip():
            raise ValueError(f"PVOG mapping has no reason for {mapping.leaf_code}")
        mappings[mapping.leaf_code] = mapping
    return payload.artifact_version, mappings


PVOG_CATEGORY_MAPPING_VERSION, _PVOG_CATEGORY_MAPPINGS = _load_category_mappings()
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
    return PvogCategoryEvidence(
        leaf_code=path.leaf_code,
        category_codes=mapping.category_codes,
        confidence=mapping.confidence,
        state=mapping.state,
        reason=mapping.reason,
        mapping_version=PVOG_CATEGORY_MAPPING_VERSION,
        source_path=path,
    )


__all__ = [
    "CategoryEvidenceState",
    "PERSONAL_MATTER_CATEGORY_CONFIDENCE",
    "PERSONAL_MATTER_TO_CATEGORY",
    "PVOG_CATEGORY_MAPPING_VERSION",
    "PvogCategoryEvidence",
    "category_evidence_for_path",
]
