"""Pydantic models for canonical category reads."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CategoryNodeRead(BaseModel):
    """A locale-resolved canonical category node and its direct children."""

    code: str
    parent_code: str | None
    name: str
    description: str
    icon: str | None
    children: list[CategoryNodeRead] = Field(default_factory=list)


class CategoryTagRead(BaseModel):
    """A canonical category attached to a document or candidate with its confidence."""

    code: str
    name: str
    confidence: float


class VocabularyTerm(BaseModel):
    """An active canonical category with every stored translation, for machine consumers."""

    code: str
    parent_code: str | None
    name_i18n: dict[str, str]
    description_i18n: dict[str, str]
    icon: str | None
    source_parent_codes: list[str]


class LegacyMappingRead(BaseModel):
    """One disposition of a legacy domain or life-situation code, served until the compatibility axes are retired."""

    axis: Literal["domain", "life_situation"]
    source_code: str
    state: Literal["mapped", "intentionally_unmapped", "manual_review"]
    target_codes: list[str]
    reason: str
    score_combination: str | None


class PvogLeafMappingRead(BaseModel):
    """One PVOG leaf and the canonical categories it maps to, with its confidence and review state."""

    leaf_code: str
    category_codes: list[str]
    confidence: float = Field(ge=0, le=1)
    state: Literal["mapped", "review"]
    reason: str


class CrosswalkRead(BaseModel):
    """The frozen PVOG leaf crosswalk with its source and artifact versions, and the legacy crosswalk."""

    artifact_version: str
    pvog_source_version: str
    pvog_leaf_mappings: list[PvogLeafMappingRead]
    legacy_crosswalk: list[LegacyMappingRead]


class VocabularyResponse(BaseModel):
    """The closed canonical category vocabulary in contract order, with the crosswalk that maps onto it."""

    categories: list[VocabularyTerm]
    crosswalk: CrosswalkRead
