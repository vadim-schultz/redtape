"""Pages candidates were found on, as the machine ``candidates/sources`` route answers them."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

SourceMissing = Literal["screenshot"]


@dataclass(frozen=True, slots=True)
class SourceQuery:
    """One page of candidate sources; ``service_ids`` (at most 20) keep rows of those procedures, ``limit`` is at most 100."""

    host: str | None
    missing: SourceMissing | None
    candidate_id: UUID | None
    service_ids: Sequence[UUID]
    offset: int
    limit: int


class CandidateSourceRead(BaseModel):
    """A procedure with candidate mentions and the page a screenshot of it should capture."""

    catalogue_service_id: UUID
    source_url: str
    host: str
    has_screenshot: bool
    mention_count: int


class CandidateSourcePage(BaseModel):
    """One page of candidate sources from the machine list route."""

    items: list[CandidateSourceRead]
    total: int
    offset: int
    limit: int
