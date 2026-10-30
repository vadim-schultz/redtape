"""Pages candidates were found on, as the machine ``candidates/sources`` route answers them."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel

SourceMissing = Literal["screenshot"]


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
