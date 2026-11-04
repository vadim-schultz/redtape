"""Types used by the versioned category contract loader."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

CategoryMappingState = Literal["mapped", "intentionally_unmapped", "manual_review"]
PVOGMappingState = Literal["mapped", "review"]
LegacyAxis = Literal["domain", "life_situation"]


class TaxonomyContractError(ValueError):
    """A category inventory or crosswalk violates the frozen contract."""


@dataclass(frozen=True, slots=True)
class CategoryDefinition:
    """One canonical product category in the frozen inventory."""

    code: str
    parent_code: str | None
    name_i18n: dict[str, str]
    description_i18n: dict[str, str]
    icon: str
    sort_order: int
    is_active: bool
    source_parent_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LegacyMapping:
    """One explicit disposition for a legacy taxonomy code."""

    axis: LegacyAxis
    source_code: str
    state: CategoryMappingState
    target_codes: tuple[str, ...]
    reason: str
    score_combination: str | None


@dataclass(frozen=True, slots=True)
class PvogLeafMapping:
    """One PVOG leaf-to-category mapping from the frozen contract."""

    leaf_code: str
    category_codes: tuple[str, ...]
    confidence: float
    state: PVOGMappingState
    reason: str


class _CategoryPayload(BaseModel):
    code: str
    parent_code: str | None
    name_i18n: dict[str, str]
    description_i18n: dict[str, str]
    icon: str
    sort_order: int
    is_active: bool
    source_parent_codes: tuple[str, ...] = ()


class _LegacyMappingPayload(BaseModel):
    axis: LegacyAxis
    source_code: str
    state: CategoryMappingState
    target_codes: tuple[str, ...] = ()
    reason: str
    score_combination: str | None = None


class _PvogLeafMappingPayload(BaseModel):
    leaf_code: str
    category_codes: tuple[str, ...]
    confidence: float
    state: PVOGMappingState
    reason: str


class _ContractPayload(BaseModel):
    artifact_version: str
    pvog_source_version: str
    categories: tuple[_CategoryPayload, ...]
    legacy_crosswalk: tuple[_LegacyMappingPayload, ...]
    pvog_leaf_mappings: tuple[_PvogLeafMappingPayload, ...] = ()
