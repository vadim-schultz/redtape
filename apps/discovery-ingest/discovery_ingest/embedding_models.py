"""Payloads of the embedding machine routes: claim text, post vectors, settle failures, count the queue."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

MAX_BATCH = 50
"""Most tasks one claim hands out and most vectors one complete call carries (the API's own bound)."""

EmbeddingOutcome = Literal["stored", "stale", "rejected"]
WorkTaskStatus = Literal["pending", "claimed", "completed", "failed"]


class EmbeddingClaimRequest(BaseModel):
    """Claim up to ``limit`` pending embedding tasks of ``model``."""

    model: str = Field(min_length=1, max_length=100)
    limit: int = Field(default=MAX_BATCH, ge=1, le=MAX_BATCH)


class ClaimedEmbeddingTask(BaseModel):
    """One leased task: the text to embed (raw, no instruction prefix) and the hash that identifies it."""

    task_id: UUID
    candidate_id: UUID
    locale: str
    text: str
    text_hash: str
    lease_expires_at: datetime


class EmbeddingClaimResponse(BaseModel):
    """The tasks one claim leased."""

    items: list[ClaimedEmbeddingTask]


class EmbeddingCompleteItem(BaseModel):
    """The vector computed for one task, tagged with the hash and model it was computed from."""

    task_id: UUID
    text_hash: str = Field(min_length=1, max_length=64)
    model: str = Field(min_length=1, max_length=100)
    vector: list[float]


class EmbeddingCompleteRequest(BaseModel):
    """A batch of computed vectors."""

    items: list[EmbeddingCompleteItem] = Field(min_length=1, max_length=MAX_BATCH)


class EmbeddingItemResult(BaseModel):
    """What completing one item did; ``reason`` explains a rejection."""

    task_id: UUID
    outcome: EmbeddingOutcome
    reason: str | None = None


class EmbeddingCompleteResponse(BaseModel):
    """One result per submitted item, in request order."""

    items: list[EmbeddingItemResult]


class EmbeddingFailRequest(BaseModel):
    """Report that a claimed task could not be embedded."""

    task_id: UUID
    error: str = Field(min_length=1, max_length=1000)
    retryable: bool = False


class EmbeddingFailResponse(BaseModel):
    """The task after the failure: ``pending`` when it will be retried, ``failed`` otherwise."""

    task_id: UUID
    status: WorkTaskStatus
    last_error: str


class EmbeddingReleaseRequest(BaseModel):
    """Hand claimed tasks back because a limit, not the text, stopped the work."""

    task_ids: list[UUID] = Field(min_length=1, max_length=MAX_BATCH)
    reason: str = Field(default="released", min_length=1, max_length=1000)


class EmbeddingReleaseResponse(BaseModel):
    """The tasks that went back to the queue and the ones this key did not hold."""

    released: list[UUID]
    skipped: list[UUID]


class EmbeddingSummary(BaseModel):
    """Queue counts for a workflow's early exit; ``stale_candidates`` are search texts without a current vector."""

    pending_ready: int
    claimed: int
    failed: int
    stale_candidates: int
