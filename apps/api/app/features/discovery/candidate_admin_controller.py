"""Read-only admin HTTP handlers for document candidates."""

from __future__ import annotations

from uuid import UUID

from litestar import Controller, get
from litestar.di import Provide

from app.features.discovery.candidate_admin_service import CandidateAdminService
from app.features.discovery.candidate_emit import DiscoveryCandidateEmitService
from app.features.discovery.candidate_list_query import CANDIDATE_LIST_SPEC, provide_candidate_query
from app.features.discovery.guards import DISCOVERY_ADMIN_GUARDS
from app.features.discovery.list_query import DiscoveryListQuery
from app.features.discovery.repository import CandidateFilter
from app.schema.discovery.candidate_edges import CandidateEdgeListResponse
from app.schema.discovery.candidate_emit import CandidateEmitPreview
from app.schema.discovery.read import CandidateDetailResponse, CandidateListResponse
from app.shared.list_query import provide_list_query


class DiscoveryCandidateAdminController(Controller):
    """Allowlisted operators review document candidates."""

    path = "/candidates"
    guards = DISCOVERY_ADMIN_GUARDS
    dependencies = {
        "list_query": provide_list_query(CANDIDATE_LIST_SPEC),
        "discovery_query": Provide(provide_candidate_query, sync_to_thread=False),
    }

    @get("/", sync_to_thread=True)
    def list_candidates(
        self,
        discovery_candidate_admin_service: CandidateAdminService,
        discovery_query: DiscoveryListQuery[CandidateFilter],
    ) -> CandidateListResponse:
        """Page through document candidates, filtered and sorted by the legacy query parameters."""
        return discovery_candidate_admin_service.list_candidates(discovery_query.filters, discovery_query.page)

    @get("/{candidate_id:uuid}", sync_to_thread=True)
    def candidate_detail(
        self,
        discovery_candidate_admin_service: CandidateAdminService,
        candidate_id: UUID,
    ) -> CandidateDetailResponse:
        """Return the detail view of one candidate."""
        return discovery_candidate_admin_service.candidate_detail(candidate_id)

    @get("/{candidate_id:uuid}/edges", sync_to_thread=True)
    def candidate_edges(
        self,
        discovery_candidate_admin_service: CandidateAdminService,
        candidate_id: UUID,
    ) -> CandidateEdgeListResponse:
        """Return every staged edge that has the candidate as its parent or its required end."""
        return discovery_candidate_admin_service.candidate_edges(candidate_id)

    @get("/{candidate_id:uuid}/emit-preview", sync_to_thread=True)
    def emit_preview(
        self,
        discovery_candidate_emit_service: DiscoveryCandidateEmitService,
        candidate_id: UUID,
    ) -> CandidateEmitPreview:
        """Return what emitting one candidate would create, without writing."""
        return discovery_candidate_emit_service.preview(candidate_id)
