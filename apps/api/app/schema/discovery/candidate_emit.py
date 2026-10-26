"""Request and response models for emitting document candidates as suggestions."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.schema.suggestion.create import SuggestionCreate

MAX_EMIT_CANDIDATES = 50


class EmitConflictRead(BaseModel):
    """A catalogue entity or pending suggestion that a candidate would duplicate."""

    type: str
    id: UUID


class CandidateEmitRequest(BaseModel):
    """Candidates to emit in one call."""

    candidate_ids: list[UUID] = Field(min_length=1, max_length=MAX_EMIT_CANDIDATES)


class CandidateEmitItemResult(BaseModel):
    """Outcome of emitting one candidate."""

    candidate_id: UUID
    suggestion_id: UUID | None = None
    skip_reason: str | None = None
    replayed: bool = False
    conflicts: list[EmitConflictRead] = Field(default_factory=list)


class CandidateEmitResponse(BaseModel):
    """Per-candidate outcomes of one emit call with their totals."""

    items: list[CandidateEmitItemResult]
    created_count: int
    skipped_count: int
    replayed_count: int


class CandidateEmitPreview(BaseModel):
    """The suggestion an emit would create, or why it would be skipped; nothing is written."""

    candidate_id: UUID
    suggestion: SuggestionCreate | None = None
    suggestion_id: UUID | None = None
    skip_reason: str | None = None
    conflicts: list[EmitConflictRead] = Field(default_factory=list)
