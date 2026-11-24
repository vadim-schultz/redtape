"""Request and response models of the translation task machine routes."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Final, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.search import WorkTaskStatus

MAX_BATCH: Final = 50
"""Most tasks one claim hands out and most translations one complete call carries."""
MAX_BODY_BYTES: Final = 2 * 1024 * 1024
"""Largest request body the translation routes read: 50 items of 4,300 characters are about 0.9 MiB at worst."""


class TranslationClaimRequest(BaseModel):
    """Claim up to ``limit`` pending translation tasks of ``engine``'s lane within a priority band, best candidates first.

    An absent ``engine`` claims without a lane, as a claim did before lanes existed. ``priority_max`` is inclusive and
    absent when the band is open above.
    """

    limit: int = Field(default=MAX_BATCH, ge=1, le=MAX_BATCH)
    engine: str | None = Field(default=None, min_length=1, max_length=50)
    priority_min: int = Field(default=0, ge=0)
    priority_max: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _band_is_ordered(self) -> TranslationClaimRequest:
        """Refuse a band whose maximum is below its minimum."""
        if self.priority_max is not None and self.priority_max < self.priority_min:
            raise ValueError("priority_max is below priority_min")
        return self


class ClaimedTranslationTask(BaseModel):
    """One leased task with the German unit to translate and the hash that identifies it."""

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
    """The text a worker produced for one task; its bounds are checked per item, not by the schema."""

    task_id: UUID
    source_hash: str = Field(min_length=1, max_length=64)
    title: str
    description: str
    engine: str = Field(min_length=1, max_length=50)
    model: str | None = Field(default=None, max_length=100)


class TranslationCompleteRequest(BaseModel):
    """A batch of translated units."""

    items: list[TranslationCompleteItem] = Field(min_length=1, max_length=MAX_BATCH)


class TranslationOutcome(enum.StrEnum):
    """What completing one item did; ``unavailable`` means the task went back to the queue untouched."""

    STORED = "stored"
    STALE = "stale"
    REJECTED = "rejected"
    UNAVAILABLE = "unavailable"


class TranslationItemResult(BaseModel):
    """The outcome of one item; ``reason`` explains a rejection or an unavailable store."""

    task_id: UUID
    outcome: TranslationOutcome
    reason: str | None = None


class TranslationCompleteResponse(BaseModel):
    """One result per submitted item, in request order."""

    items: list[TranslationItemResult]


class TranslationFailRequest(BaseModel):
    """A worker's report that it could not translate a task."""

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
    """Queue and store counts of one target locale.

    ``stale`` counts stored translations that an open task is replacing with a newer German unit. The age of the
    oldest ready task is ``null`` when none is ready; ``completed_24h`` and ``failed_24h`` count the last day.
    """

    locale: str
    pending_ready: int
    claimed: int
    failed: int
    stale: int
    translated: int
    oldest_pending_age_seconds: float | None
    completed_24h: int
    failed_24h: int


class TranslationSummaryResponse(BaseModel):
    """Counts per target locale, in the configured order, so a workflow can stop early when nothing is ready."""

    locales: list[TranslationLocaleSummary]
