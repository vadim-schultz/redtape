"""DTOs mirroring the discovery machine routes that select and emit document candidates."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from discovery_ingest.mentions import MentionRole

MAX_EMIT_CANDIDATES = 50


class EmitConflict(BaseModel):
    """A document or pending suggestion that a candidate would duplicate."""

    type: str
    id: UUID


class CandidateSummary(BaseModel):
    """One staged candidate from ``GET /candidates``: its key, titles and the roles it was mentioned in."""

    id: UUID
    jurisdiction_id: UUID
    key: str
    title_i18n: dict[str, str]
    roles: list[MentionRole]
    mention_count: int


class CandidatePage(BaseModel):
    """A page of staged candidates, most mentioned first."""

    items: list[CandidateSummary]
    total: int


class EmitRequest(BaseModel):
    """Body of ``POST /candidates/emit``."""

    candidate_ids: list[UUID] = Field(min_length=1, max_length=MAX_EMIT_CANDIDATES)


class EmitItem(BaseModel):
    """Outcome of emitting one candidate."""

    candidate_id: UUID
    suggestion_id: UUID | None = None
    skip_reason: str | None = None
    replayed: bool = False
    conflicts: list[EmitConflict] = Field(default_factory=list)


class EmitResponse(BaseModel):
    """Outcomes of one emit call with their totals."""

    items: list[EmitItem]
    created_count: int
    skipped_count: int
    replayed_count: int


class EmitPreview(BaseModel):
    """What an emit would create for one candidate, or why it would be skipped."""

    candidate_id: UUID
    suggestion: dict[str, object] | None = None
    suggestion_id: UUID | None = None
    skip_reason: str | None = None
    conflicts: list[EmitConflict] = Field(default_factory=list)
