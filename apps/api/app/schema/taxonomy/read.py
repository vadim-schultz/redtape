"""Pydantic models for canonical category reads."""

from __future__ import annotations

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


class VocabularyResponse(BaseModel):
    """The closed canonical category vocabulary in contract order."""

    categories: list[VocabularyTerm]
