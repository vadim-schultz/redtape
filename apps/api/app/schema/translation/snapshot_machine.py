"""Request and response models of the snapshot machine routes: claim pages by reference, complete them by outcome.

A worker reads a claimed page through the artifact route, translates its cleaned text as blocks and posts the result.
The fail and release routes are the card routes' models, since a leased task settles the same way in both tables.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Annotated, Final, Literal
from uuid import UUID

from pydantic import BaseModel, Field

MAX_SNAPSHOT_BATCH: Final = 5
"""Most snapshot tasks one claim hands out and most items one complete call carries: the 2 MiB body cap allows five."""


class TextBlock(BaseModel):
    """A block of translated text: a heading, a paragraph, a list item or a definition term."""

    kind: Literal["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "dt"]
    text: str


class RowBlock(BaseModel):
    """A table row: its cells in source order."""

    kind: Literal["row"]
    cells: list[str]


SnapshotBlock = Annotated[TextBlock | RowBlock, Field(discriminator="kind")]
"""One block of a page, discriminated by its kind; a row carries cells, every other kind carries text."""


class SnapshotClaimRequest(BaseModel):
    """Claim up to ``limit`` pending snapshot tasks, highest-priority pages first."""

    limit: int = Field(default=MAX_SNAPSHOT_BATCH, ge=1, le=MAX_SNAPSHOT_BATCH)


class ClaimedSnapshotTask(BaseModel):
    """One leased page task: the artifact to read, its hash, and the hash of the text already stored, if any."""

    task_id: UUID
    catalogue_service_id: UUID
    locale: str
    source_locale: Literal["de"] = "de"
    artifact_id: UUID
    artifact_sha256: str
    source_url: str
    stored_source_hash: str | None
    lease_expires_at: datetime


class SnapshotClaimResponse(BaseModel):
    """The snapshot tasks one claim leased."""

    items: list[ClaimedSnapshotTask]


class SnapshotItemOutcome(enum.StrEnum):
    """What a worker reports for one claimed page: translated blocks, unchanged cleaned text, or a skipped page."""

    TRANSLATED = "translated"
    UNCHANGED = "unchanged"
    SKIPPED = "skipped"


class SnapshotSkipReason(enum.StrEnum):
    """Why a page is not translated: its cleaned text is too short, or its language is not German."""

    TOO_SHORT = "too_short"
    NOT_GERMAN = "not_german"


class SnapshotCompleteItem(BaseModel):
    """The result for one claimed page; its bounds and the presence of its fields are checked per item, not by the schema.

    A translated item carries ``blocks``, ``engine`` and ``truncated``; a skipped item carries ``skipped_reason``.
    """

    task_id: UUID
    artifact_sha256: str = Field(min_length=64, max_length=64)
    source_hash: str = Field(min_length=1, max_length=64)
    outcome: SnapshotItemOutcome
    blocks: list[SnapshotBlock] | None = None
    truncated: bool = False
    engine: str | None = Field(default=None, min_length=1, max_length=50)
    model: str | None = Field(default=None, max_length=100)
    skipped_reason: SnapshotSkipReason | None = None


class SnapshotCompleteRequest(BaseModel):
    """A batch of page results, at most five, so the body stays under the 2 MiB cap."""

    items: list[SnapshotCompleteItem] = Field(min_length=1, max_length=MAX_SNAPSHOT_BATCH)


class SnapshotAnswer(enum.StrEnum):
    """What completing one item did; ``unavailable`` means the task went back to the queue without an attempt."""

    STORED = "stored"
    UNCHANGED = "unchanged"
    SKIPPED = "skipped"
    STALE = "stale"
    REJECTED = "rejected"
    UNAVAILABLE = "unavailable"


class SnapshotItemResult(BaseModel):
    """The answer for one item; ``reason`` explains a stale, rejected or unavailable answer."""

    task_id: UUID
    outcome: SnapshotAnswer
    reason: str | None = None


class SnapshotCompleteResponse(BaseModel):
    """One answer per submitted item, in request order."""

    items: list[SnapshotItemResult]


class SnapshotLocaleSummary(BaseModel):
    """Queue and store counts of one target locale for snapshot pages.

    ``stale`` counts translated pages that an open task is replacing with a newer artifact; ``skipped`` counts markers.
    """

    locale: str
    pending_ready: int
    claimed: int
    failed: int
    translated: int
    stale: int
    skipped: int


class SnapshotSummaryResponse(BaseModel):
    """Counts per target locale, in the configured order, so a workflow can stop early when nothing is ready."""

    locales: list[SnapshotLocaleSummary]
