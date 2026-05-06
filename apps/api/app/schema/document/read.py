"""Pydantic models for document API (read-only MVP)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentListQuery(BaseModel):
    """Query parameters for listing documents."""

    jurisdiction_id: UUID | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class DocumentSummary(BaseModel):
    """Lightweight document for lists and references."""

    model_config = ConfigDict(from_attributes=False)

    id: UUID
    slug: str
    title: str
    description: str


class RequirementRead(BaseModel):
    """Requirement edge with resolved required document."""

    model_config = ConfigDict(from_attributes=False)

    id: UUID
    required_document: DocumentSummary
    notes: str | None


class DocumentDetail(BaseModel):
    """Full document with direct requirements."""

    model_config = ConfigDict(from_attributes=False)

    id: UUID
    slug: str
    title: str
    description: str
    official_url: str | None
    jurisdiction_id: UUID
    requirements: list[RequirementRead] = Field(default_factory=list)


class DocumentListResponse(BaseModel):
    """Paginated list response."""

    items: list[DocumentSummary]
    total: int
    offset: int
    limit: int
