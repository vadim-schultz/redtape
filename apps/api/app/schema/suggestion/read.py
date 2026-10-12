"""Response schema for suggestions; reused by chapters 6-7."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.suggestion import Suggestion, SuggestionKind, SuggestionSource, SuggestionStatus
from app.schema.document.read import JurisdictionPathNode

_SUBMITTER_KIND: dict[SuggestionSource, Literal["user", "crawler"]] = {
    SuggestionSource.HUMAN: "user",
    SuggestionSource.CRAWLER: "crawler",
}


class SubmitterRead(BaseModel):
    """Who submitted a suggestion; never the email or key (D7)."""

    model_config = ConfigDict(from_attributes=False)

    kind: Literal["user", "crawler"]
    display_name: str | None = None


class ConflictRead(BaseModel):
    """A catalogue entity that already matches an incoming suggestion (D4)."""

    model_config = ConfigDict(from_attributes=False)

    type: Literal["document", "suggestion", "document_requirement"]
    id: UUID


class Tally(BaseModel):
    """Vote counts for a suggestion; always computed, never cached (D3)."""

    model_config = ConfigDict(from_attributes=False)

    up: int
    down: int
    score: int


class SuggestionRead(BaseModel):
    """`POST /api/v1/suggestions` response body (architecture §5)."""

    model_config = ConfigDict(from_attributes=False)

    id: UUID
    kind: SuggestionKind
    status: SuggestionStatus
    source_type: SuggestionSource
    jurisdiction_id: UUID
    jurisdiction_path: list[JurisdictionPathNode] = Field(default_factory=list)
    payload: dict
    source_url: str | None
    submitted_by: SubmitterRead
    created_at: datetime
    tally: Tally = Field(default_factory=lambda: Tally(up=0, down=0, score=0))
    my_vote: int | None = None

    @classmethod
    def from_row(
        cls,
        suggestion: Suggestion,
        *,
        submitter_display_name: str | None,
        jurisdiction_path: list[JurisdictionPathNode] | None = None,
    ) -> SuggestionRead:
        submitted_by = SubmitterRead(
            kind=_SUBMITTER_KIND[suggestion.source_type], display_name=submitter_display_name or None
        )
        return cls(
            id=suggestion.id,
            kind=suggestion.kind,
            status=suggestion.status,
            source_type=suggestion.source_type,
            jurisdiction_id=suggestion.jurisdiction_id,
            jurisdiction_path=jurisdiction_path or [],
            payload=suggestion.payload,
            source_url=suggestion.source_url,
            submitted_by=submitted_by,
            created_at=suggestion.created_at,
        )


class SuggestionListResponse(BaseModel):
    """`GET /api/v1/suggestions` response body (chapter 7)."""

    items: list[SuggestionRead]
    total: int
    offset: int
    limit: int
