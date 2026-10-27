"""Map emit outcomes of a document candidate to its result models."""

from __future__ import annotations

from uuid import UUID

from app.features.discovery.candidate_emit_skip import EmitSkip
from app.schema.discovery.candidate_emit import CandidateEmitItemResult, CandidateEmitResponse, EmitConflictRead
from app.schema.discovery.emit import tally_outcomes


def idempotency_key(candidate_id: UUID) -> str:
    """Return the key under which ``candidate_id`` is submitted, so a replay finds its suggestion."""
    return f"discovery-candidate-emit:{candidate_id}"


def conflict_reads(skip: EmitSkip) -> list[EmitConflictRead]:
    """Return the conflicts behind ``skip`` in their response shape."""
    return [EmitConflictRead(type=conflict.type, id=conflict.id) for conflict in skip.conflicts]


def skipped(candidate_id: UUID, skip: EmitSkip) -> CandidateEmitItemResult:
    """Return the result of a candidate that was not emitted because of ``skip``."""
    return CandidateEmitItemResult(candidate_id=candidate_id, skip_reason=skip.reason, conflicts=conflict_reads(skip))


def emitted(candidate_id: UUID, suggestion_id: UUID | None, *, replayed: bool) -> CandidateEmitItemResult:
    """Return the result of a candidate whose suggestion exists."""
    return CandidateEmitItemResult(candidate_id=candidate_id, suggestion_id=suggestion_id, replayed=replayed)


def tally(items: list[CandidateEmitItemResult]) -> CandidateEmitResponse:
    """Return ``items`` with their created, skipped and replayed totals."""
    return CandidateEmitResponse(items=items, **tally_outcomes(items).model_dump())
