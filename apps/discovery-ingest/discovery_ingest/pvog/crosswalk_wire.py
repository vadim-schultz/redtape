"""Wire shape of the machine taxonomy's crosswalk section, as the API serves it."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from discovery_ingest.pvog.category_mapping import CategoryEvidenceState, LegacyAxis


class ServedCategory(BaseModel):
    """A served category: its code and the PVOG parent codes it is the target of."""

    code: str
    source_parent_codes: tuple[str, ...] = ()


class ServedLeafMapping(BaseModel):
    """One PVOG leaf and the canonical categories it maps to, with its confidence and review state."""

    leaf_code: str
    category_codes: tuple[str, ...]
    confidence: float = Field(ge=0, le=1)
    state: CategoryEvidenceState
    reason: str


class ServedLegacyMapping(BaseModel):
    """One disposition of a legacy domain or life-situation code."""

    axis: LegacyAxis
    source_code: str
    state: Literal["mapped", "intentionally_unmapped", "manual_review"]
    target_codes: tuple[str, ...] = ()
    reason: str
    score_combination: str | None = None


class ServedCrosswalk(BaseModel):
    """The crosswalk section: the source and artifact versions, the PVOG leaves and the legacy dispositions."""

    artifact_version: str
    pvog_source_version: str
    pvog_leaf_mappings: tuple[ServedLeafMapping, ...]
    legacy_crosswalk: tuple[ServedLegacyMapping, ...]


class ServedVocabulary(BaseModel):
    """The machine taxonomy as the crosswalk reads it: the served categories and the crosswalk section."""

    categories: tuple[ServedCategory, ...]
    crosswalk: ServedCrosswalk
