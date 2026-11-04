"""Pydantic models for canonical and legacy taxonomy reads."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TermRead(BaseModel):
    """A locale-resolved domain or life situation."""

    code: str
    name: str
    description: str
    icon: str | None


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


class LifeSituationGroupedRead(TermRead):
    """A locale-resolved life situation, carrying its presentational group's code."""

    group_code: str


class MatrixCell(BaseModel):
    """Documents tagged with both a domain and a life situation."""

    domain: str
    situation: str
    count: int


class AxisCount(BaseModel):
    """Distinct documents carrying one term, however many other terms they also carry."""

    code: str
    count: int


class MatrixResponse(BaseModel):
    """Non-empty cells plus distinct-document totals per axis term and overall."""

    total: int
    cells: list[MatrixCell]
    situations: list[AxisCount]
    domains: list[AxisCount]


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
