"""Read-only admin HTTP handlers for document candidates."""

from __future__ import annotations

from uuid import UUID

from litestar import Controller, get
from litestar.params import Parameter

from app.features.discovery.candidate_admin_service import CandidateAdminService
from app.features.discovery.guards import DISCOVERY_ADMIN_GUARDS
from app.models.discovery import DiscoveryCandidateStatus
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
    ) -> CandidateListResponse:
        return discovery_candidate_admin_service.list_candidates(status=status, offset=page.offset, limit=page.limit)

    @get("/{candidate_id:uuid}", sync_to_thread=True)
    def candidate_detail(
        self,
        discovery_candidate_admin_service: CandidateAdminService,
        candidate_id: UUID,
    ) -> CandidateDetailResponse:
        return discovery_candidate_admin_service.candidate_detail(candidate_id)
