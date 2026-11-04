"""Query provider for the machine candidate sources listing."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from litestar.params import Parameter

from app.features.discovery.list_query import DiscoveryListQuery
from app.features.discovery.repository import CandidateSourceFilter, Page
from app.shared.paging import PageParams


def provide_candidate_source_query(
    page: PageParams,
    missing: Literal["screenshot"] | None = Parameter(query="missing", default=None),
    host: str | None = Parameter(query="host", default=None, min_length=1, max_length=253),
    candidate_id: UUID | None = Parameter(query="candidate_id", default=None),
    service_ids: list[UUID] | None = Parameter(query="catalogue_service_id", default=None, max_items=20),
) -> DiscoveryListQuery[CandidateSourceFilter]:
    """Collect the candidate source list parameters into one filter and page."""
    candidate_filter = CandidateSourceFilter(
        missing_screenshot=missing == "screenshot",
        host=host,
        candidate_id=candidate_id,
        service_ids=service_ids or (),
    )
    return DiscoveryListQuery(filters=candidate_filter, page=Page(offset=page.offset, limit=page.limit))
