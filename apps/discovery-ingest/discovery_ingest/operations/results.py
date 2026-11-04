"""Typed outcomes of the ingest operations; the command layer renders them."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True, slots=True)
class IngestResult:
    """What one catalogue ingest posted and what it skipped."""

    source: str
    rows_posted: int
    rows_skipped: int
    skipped: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class EnrichResult:
    """The entity an enrich run upserted and how many claims it appended to it."""

    entity_id: UUID
    claims_posted: int
