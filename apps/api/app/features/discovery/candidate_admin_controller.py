"""Read-only admin HTTP handlers for document candidates."""

from __future__ import annotations

from uuid import UUID

from litestar import Controller, get
from litestar.params import Parameter

from app.features.discovery.candidate_admin_service import CandidateAdminService
from app.features.discovery.candidate_emit import DiscoveryCandidateEmitService
from app.features.discovery.guards import DISCOVERY_ADMIN_GUARDS
from app.features.discovery.repository import CandidateFilter, CandidateSort, Page
from app.models.discovery import DiscoveryCandidateStatus, DiscoveryMentionRole, DiscoverySource
from app.schema.discovery.candidate_emit import CandidateEmitPreview
from app.schema.discovery.read import CandidateDetailResponse, CandidateListResponse
from app.shared.paging import PageParams


class DiscoveryCandidateAdminController(Controller):
    """Allowlisted operators review document candidates."""

    path = "/candidates"
    guards = DISCOVERY_ADMIN_GUARDS

    @get("/", sync_to_thread=True)
    def list_candidates(
        self,
        discovery_candidate_admin_service: CandidateAdminService,
        page: PageParams,
        status: DiscoveryCandidateStatus | None = Parameter(query="status", default=None),
        q: str | None = Parameter(query="q", default=None, min_length=1, max_length=200),
        min_mentions: int | None = Parameter(query="min_mentions", default=None, ge=0),
        role: DiscoveryMentionRole | None = Parameter(query="role", default=None),
        source: DiscoverySource | None = Parameter(query="source", default=None),
        sort: CandidateSort = Parameter(query="sort", default=CandidateSort.MENTIONS_DESC),
    ) -> CandidateListResponse:
        candidate_filter = CandidateFilter(
            status=status, q=q, min_mentions=min_mentions, role=role, source=source, sort=sort
        )
        return discovery_candidate_admin_service.list_candidates(
            candidate_filter, Page(offset=page.offset, limit=page.limit)
        )

    @get("/{candidate_id:uuid}", sync_to_thread=True)
    def candidate_detail(
        self,
        discovery_candidate_admin_service: CandidateAdminService,
        candidate_id: UUID,
    ) -> CandidateDetailResponse:
        return discovery_candidate_admin_service.candidate_detail(candidate_id)

    @get("/{candidate_id:uuid}/emit-preview", sync_to_thread=True)
    def emit_preview(
        self,
        discovery_candidate_emit_service: DiscoveryCandidateEmitService,
        candidate_id: UUID,
    ) -> CandidateEmitPreview:
        return discovery_candidate_emit_service.preview(candidate_id)
