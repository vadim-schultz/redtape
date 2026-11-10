"""Request and response models for emitting document candidates as suggestions."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.models.suggestion import SuggestionKind
from app.schema.discovery.emit import EmitCounts, EmitOutcome, SkipReason
from app.schema.locale.keys import LocaleKeyedMap
from app.schema.suggestion.create import SuggestionCreate

MAX_EMIT_CANDIDATES = 50


class EmitConflictRead(BaseModel):
    """A catalogue entity or pending suggestion that a candidate would duplicate."""

    type: str
    id: UUID


class CandidateEmitRequest(BaseModel):
    """Candidates to emit in one call."""

    candidate_ids: list[UUID] = Field(min_length=1, max_length=MAX_EMIT_CANDIDATES)


class CandidateEmitItemResult(EmitOutcome):
    """Outcome of emitting one candidate."""

    candidate_id: UUID
    conflicts: list[EmitConflictRead] = Field(default_factory=list)


class CandidateEmitResponse(EmitCounts):
    """Per-candidate outcomes of one emit call with their totals."""

    items: list[CandidateEmitItemResult]


class PreviewedDocumentPayload(BaseModel):
    """The canonical ``new_document`` fields an emit preview shows; legacy axis inputs are never output."""

    title_i18n: LocaleKeyedMap
    description_i18n: LocaleKeyedMap | None = None
    official_url: str | None = None
    category_codes: list[str] = Field(default_factory=list)
    tag_confidence: dict[str, float] | None = None
    pvog_leaf_codes: dict[str, str] | None = None


class PreviewedSuggestion(BaseModel):
    """The suggestion an emit would create, with the canonical payload only."""

    kind: SuggestionKind
    jurisdiction_id: UUID | None = None
    municipality_code: str | None = None
    source_url: str | None = None
    payload: PreviewedDocumentPayload

    @classmethod
    def from_request(cls, request: SuggestionCreate) -> PreviewedSuggestion:
        """Return the preview of ``request``, dropping its compatibility-only fields."""
        return cls(
            kind=request.kind,
            jurisdiction_id=request.jurisdiction_id,
            municipality_code=request.municipality_code,
            source_url=request.source_url,
            payload=PreviewedDocumentPayload.model_validate(request.payload.model_dump()),
        )


class CandidateEmitPreview(BaseModel):
    """The suggestion an emit would create, or why it would be skipped; nothing is written."""

    candidate_id: UUID
    suggestion: PreviewedSuggestion | None = None
    suggestion_id: UUID | None = None
    skip_reason: SkipReason | None = None
    conflicts: list[EmitConflictRead] = Field(default_factory=list)
