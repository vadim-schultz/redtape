"""Response models of the machine route that lists the pages candidates were found on."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class CandidateSourceRead(BaseModel):
    """A procedure with candidate mentions and the page a screenshot of it should capture."""

    catalogue_service_id: UUID
    source_url: str
    host: str
    has_screenshot: bool
    mention_count: int


class CandidateSourceListResponse(BaseModel):
    """One page of candidate sources."""

    items: list[CandidateSourceRead]
    total: int
    offset: int
    limit: int
