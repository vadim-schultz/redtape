"""Read models of the public candidate API: a ranked card, and the detail with its neighbours and sources."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.discovery import DiscoveryCandidateStatus, DiscoveryEdgeBasis, DiscoveryMentionRole


class CandidateTag(BaseModel):
    """An accepted taxonomy code with its localized name."""

    model_config = ConfigDict(from_attributes=False)

    code: str
    name: str


class CandidateFlags(BaseModel):
    """The five completeness flags of a candidate."""

    model_config = ConfigDict(from_attributes=False)

    has_domain: bool
    has_situation: bool
    has_edges: bool
    has_snapshot: bool
    has_screenshot: bool


class CandidateCard(BaseModel):
    """One candidate in the ranked list."""

    model_config = ConfigDict(from_attributes=False)

    id: UUID
    key: str
    title: str
    description: str | None
    description_source: str | None
    status: DiscoveryCandidateStatus
    domains: list[CandidateTag]
    situations: list[CandidateTag]
    completeness: int
    complete: bool
    flags: CandidateFlags
    mention_count: int


class CandidateListResponse(BaseModel):
    """One page of candidate cards; ``total`` counts the full filtered result."""

    model_config = ConfigDict(from_attributes=False)

    items: list[CandidateCard]
    total: int
    offset: int
    limit: int


class CandidateNeighbour(BaseModel):
    """A document one edge away, merged over the procedures that state the edge."""

    model_config = ConfigDict(from_attributes=False)

    id: UUID
    title: str
    description: str | None
    condition: str | None
    is_optional: bool
    excerpt: str
    basis: DiscoveryEdgeBasis
    procedure_title: str


class CandidateSource(BaseModel):
    """The best mention of the candidate on one procedure; ``portal_url`` is only ever http or https."""

    model_config = ConfigDict(from_attributes=False)

    procedure_title: str
    portal_url: str | None
    role: DiscoveryMentionRole
    excerpt: str
    condition: str | None
    is_optional: bool


class CandidateScreenshot(BaseModel):
    """The relative public proxy path of the newest screenshot and when it was fetched."""

    model_config = ConfigDict(from_attributes=False)

    url: str
    fetched_at: datetime


class CandidateDetail(CandidateCard):
    """A candidate with the documents it needs (ingress) and the documents that need it (egress)."""

    ingress: list[CandidateNeighbour] = Field(default_factory=list)
    ingress_truncated: bool = False
    egress: list[CandidateNeighbour] = Field(default_factory=list)
    egress_truncated: bool = False
    sources: list[CandidateSource] = Field(default_factory=list)
    screenshot: CandidateScreenshot | None = None
