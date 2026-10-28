"""Pydantic models for the taxonomy API (read-only)."""

from __future__ import annotations

from pydantic import BaseModel


class TermRead(BaseModel):
    """A locale-resolved domain or life situation."""

    code: str
    name: str
    description: str
    icon: str | None


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
    """A domain or life situation with every stored translation, for machine consumers."""

    code: str
    name_i18n: dict[str, str]
    description_i18n: dict[str, str]


class VocabularyResponse(BaseModel):
    """Both closed vocabularies in sort order."""

    domains: list[VocabularyTerm]
    situations: list[VocabularyTerm]
