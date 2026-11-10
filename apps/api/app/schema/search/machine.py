"""Request and response models of the embedding task machine routes."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Final
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.search import WorkTaskStatus

MAX_BATCH: Final = 50
"""Most tasks one claim hands out and most vectors one complete call carries."""
MAX_BODY_BYTES: Final = 2 * 1024 * 1024
"""Largest request body the embedding routes read: a full batch of 50 vectors is well under 1 MiB."""


class EmbeddingClaimRequest(BaseModel):
    """Claim up to ``limit`` pending embedding tasks of ``model``."""

    limit: int = Field(default=MAX_BATCH, ge=1, le=MAX_BATCH)
    model: str = Field(min_length=1, max_length=100)


class ClaimedEmbeddingTask(BaseModel):
    """One leased task with the text to embed and the hash that identifies it."""

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
    """The vector a worker computed for one task; its length is checked per item, not by the schema."""

    task_id: UUID
    text_hash: str = Field(min_length=1, max_length=64)
    model: str = Field(min_length=1, max_length=100)
    vector: list[float]


class EmbeddingCompleteRequest(BaseModel):
    """A batch of computed vectors."""

    items: list[EmbeddingCompleteItem] = Field(min_length=1, max_length=MAX_BATCH)


class EmbeddingOutcome(enum.StrEnum):
    """What completing one item did."""

    STORED = "stored"
    STALE = "stale"
    REJECTED = "rejected"


class EmbeddingItemResult(BaseModel):
    """The outcome of one item; ``reason`` explains a rejection."""

    task_id: UUID
    outcome: EmbeddingOutcome
    reason: str | None = None


class EmbeddingCompleteResponse(BaseModel):
    """One result per submitted item, in request order."""

    items: list[EmbeddingItemResult]


class EmbeddingFailRequest(BaseModel):
    """A worker's report that it could not embed a task."""

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


class EmbeddingSummaryResponse(BaseModel):
    """Queue counts for a workflow's early exit; ``stale_candidates`` are search texts without a current vector."""

    pending_ready: int
    claimed: int
    failed: int
    stale_candidates: int
