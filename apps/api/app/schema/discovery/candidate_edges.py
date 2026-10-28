"""Request and response models for staged requirement edges."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.discovery import DiscoveryEdgeBasis
from app.schema.discovery.candidates import MAX_CONDITION_LENGTH, MAX_MENTION_ITEMS

EdgeSkipReason = Literal["blank_excerpt", "same_endpoints", "unknown_parent", "unknown_required"]


class CandidateEdgeItem(BaseModel):
    """One ``parent requires required`` edge stated by a procedure."""

    catalogue_service_id: UUID
    parent_title_i18n: dict[str, str] = Field(min_length=1)
    required_title_i18n: dict[str, str] = Field(min_length=1)
    basis: DiscoveryEdgeBasis
    condition: str | None = Field(default=None, min_length=1, max_length=MAX_CONDITION_LENGTH)
    is_optional: bool | None = None
    excerpt: str
    extractor: str = Field(min_length=1, max_length=64)
    extractor_version: str = Field(min_length=1, max_length=32)


class CandidateEdgesRequest(BaseModel):
    """Batch of edges; each item is settled on its own."""

    items: list[CandidateEdgeItem] = Field(min_length=1, max_length=MAX_MENTION_ITEMS)


class EdgeSkip(BaseModel):
    """Why the item at ``index`` was not recorded."""

    index: int
    reason: EdgeSkipReason


class CandidateEdgesResponse(BaseModel):
    """What an edge batch created, updated or skipped."""

    edges_created: int
    edges_updated: int
    edges_skipped: int
    skipped: list[EdgeSkip]


class CandidateEdgeRead(BaseModel):
    """A staged edge with both candidate titles and the procedure that states it."""

    model_config = ConfigDict(from_attributes=False)

    id: UUID
    parent_candidate_id: UUID
    parent_title_i18n: dict[str, str]
    required_candidate_id: UUID
    required_title_i18n: dict[str, str]
    catalogue_service_id: UUID
    procedure_title_i18n: dict[str, str]
    basis: DiscoveryEdgeBasis
    condition: str | None
    is_optional: bool | None
    excerpt: str
    extractor: str
    extractor_version: str
    created_at: datetime


class CandidateEdgeListResponse(BaseModel):
    """Every edge that has the candidate as parent or as required end."""

    items: list[CandidateEdgeRead]
