"""Payloads of the translation machine routes: claim German units, post translated text, settle failures, count the queue."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

MAX_BATCH = 50
"""Most tasks one claim hands out and most translations one complete call carries (the API's own bound)."""

TranslationOutcome = Literal["stored", "stale", "rejected", "unavailable"]
WorkTaskStatus = Literal["pending", "claimed", "completed", "failed"]


class TranslationClaimRequest(BaseModel):
    """Claim up to ``limit`` pending translation tasks, highest-priority candidates first."""

    limit: int = Field(default=MAX_BATCH, ge=1, le=MAX_BATCH)


class ClaimedTranslationTask(BaseModel):
    """One leased task: the German unit to translate and the hash that identifies it."""

    task_id: UUID
    candidate_id: UUID
    locale: str
    source_locale: Literal["de"] = "de"
    title: str
    description: str
    source_hash: str
    lease_expires_at: datetime


class TranslationClaimResponse(BaseModel):
    """The tasks one claim leased."""

    items: list[ClaimedTranslationTask]


class TranslationCompleteItem(BaseModel):
    """The text produced for one task, tagged with the hash it was made from and the engine and model that made it."""

    task_id: UUID
    source_hash: str = Field(min_length=1, max_length=64)
    title: str
    description: str
    engine: str = Field(min_length=1, max_length=50)
    model: str | None = Field(default=None, max_length=100)


class TranslationCompleteRequest(BaseModel):
    """A batch of translated units."""

    items: list[TranslationCompleteItem] = Field(min_length=1, max_length=MAX_BATCH)


class TranslationItemResult(BaseModel):
    """What completing one item did; ``reason`` explains a rejection or an unavailable store."""

    task_id: UUID
    outcome: TranslationOutcome
    reason: str | None = None


class TranslationCompleteResponse(BaseModel):
    """One result per submitted item, in request order."""

    items: list[TranslationItemResult]


class TranslationFailRequest(BaseModel):
    """Report that a claimed task could not be translated."""

    task_id: UUID
    error: str = Field(min_length=1, max_length=1000)
    retryable: bool = False


class TranslationFailResponse(BaseModel):
    """The task after the failure: ``pending`` when it will be retried, ``failed`` otherwise."""

    task_id: UUID
    status: WorkTaskStatus
    last_error: str


class TranslationReleaseRequest(BaseModel):
    """Hand claimed tasks back because a limit, not the text, stopped the work."""

    task_ids: list[UUID] = Field(min_length=1, max_length=MAX_BATCH)
    reason: str = Field(default="released", min_length=1, max_length=1000)


class TranslationReleaseResponse(BaseModel):
    """The tasks that went back to the queue and the ones this key did not hold."""

    released: list[UUID]
    skipped: list[UUID]


class TranslationLocaleSummary(BaseModel):
    """Queue and store counts of one target locale."""

    locale: str
    pending_ready: int
    claimed: int
    failed: int
    stale: int
    translated: int


class TranslationSummary(BaseModel):
    """Counts per target locale, in the API's configured order, for a workflow's early exit."""

    locales: list[TranslationLocaleSummary]

    @property
    def pending_ready(self) -> int:
        """Tasks ready to be claimed across every target locale."""
        return sum(row.pending_ready for row in self.locales)
