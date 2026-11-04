"""Machine HTTP handlers for document candidates."""

from __future__ import annotations

from uuid import UUID

from litestar import Controller, get, post
from litestar.di import Provide
from litestar.status_codes import HTTP_200_OK

from app.features.auth.principal import MachinePrincipal
from app.features.discovery.candidate_admin_service import CandidateAdminService
from app.features.discovery.candidate_emit import DiscoveryCandidateEmitService
from app.features.discovery.candidate_list_query import provide_machine_candidate_query
from app.features.discovery.candidate_service import CandidateService
from app.features.discovery.candidate_source_query import provide_candidate_source_query
from app.features.discovery.db_headroom import DB_WRITE_GUARDS
from app.features.discovery.edge_service import EdgeService
from app.features.discovery.guards import require_discovery_machine
from app.features.discovery.list_query import DiscoveryListQuery
from app.features.discovery.repository import CandidateFilter, CandidateSourceFilter
from app.schema.discovery.candidate_edges import CandidateEdgesRequest, CandidateEdgesResponse
from app.schema.discovery.candidate_emit import CandidateEmitPreview, CandidateEmitRequest, CandidateEmitResponse
from app.schema.discovery.candidate_sources import CandidateSourceListResponse
from app.schema.discovery.candidates import CandidateMentionsRequest, CandidateMentionsResponse
from app.schema.discovery.read import CandidateListResponse


class DiscoveryCandidateMachineController(Controller):
    """Workers report where documents are mentioned and emit reviewed candidates."""

    path = "/candidates"
    guards = [require_discovery_machine]

    @post("/mentions", sync_to_thread=True, status_code=HTTP_200_OK, guards=DB_WRITE_GUARDS)
    def record_mentions(
        self,
        discovery_candidate_service: CandidateService,
        data: CandidateMentionsRequest,
    ) -> CandidateMentionsResponse:
        """Record where documents are mentioned on catalogue procedures; the batch is written all or nothing."""
        return discovery_candidate_service.record_mentions(data)

    @post("/edges", sync_to_thread=True, status_code=HTTP_200_OK, guards=DB_WRITE_GUARDS)
    def record_edges(
        self,
        discovery_edge_service: EdgeService,
        data: CandidateEdgesRequest,
    ) -> CandidateEdgesResponse:
        """Record staged edges between candidates; an unknown catalogue row rejects the batch before any write."""
        return discovery_edge_service.record_edges(data)

    @get(
        "/",
        sync_to_thread=True,
        dependencies={"discovery_query": Provide(provide_machine_candidate_query, sync_to_thread=False)},
    )
    def select_candidates(
        self,
        discovery_candidate_admin_service: CandidateAdminService,
        discovery_query: DiscoveryListQuery[CandidateFilter],
    ) -> CandidateListResponse:
        """Page through candidates for workers, optionally filtered by status and minimum mentions."""
        return discovery_candidate_admin_service.list_candidates(discovery_query.filters, discovery_query.page)

    @get(
        "/sources",
        sync_to_thread=True,
        dependencies={"discovery_query": Provide(provide_candidate_source_query, sync_to_thread=False)},
    )
    def select_candidate_sources(
        self,
        discovery_candidate_admin_service: CandidateAdminService,
        discovery_query: DiscoveryListQuery[CandidateSourceFilter],
    ) -> CandidateSourceListResponse:
        """Page through procedures with candidate mentions, narrowed by missing screenshot, host or candidate."""
        return discovery_candidate_admin_service.list_candidate_sources(discovery_query.filters, discovery_query.page)

    @get("/{candidate_id:uuid}/emit-preview", sync_to_thread=True)
    def preview_emit(
        self,
        discovery_candidate_emit_service: DiscoveryCandidateEmitService,
        candidate_id: UUID,
    ) -> CandidateEmitPreview:
        """Return what emitting one candidate would create, for workers, without writing."""
        return discovery_candidate_emit_service.preview(candidate_id)

    @post("/emit", sync_to_thread=True, status_code=HTTP_200_OK)
    def emit_candidates(
        self,
        discovery_candidate_emit_service: DiscoveryCandidateEmitService,
        machine_principal: MachinePrincipal,
        data: CandidateEmitRequest,
    ) -> CandidateEmitResponse:
        """Emit a batch of candidates under the machine's API key and total the outcomes."""
        return discovery_candidate_emit_service.emit_batch(data.candidate_ids, machine_principal.api_key)
