"""Machine HTTP handlers for document candidates."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from litestar import Controller, get, post
from litestar.params import Parameter
from litestar.status_codes import HTTP_200_OK

from app.features.auth.principal import MachinePrincipal
from app.features.discovery.candidate_admin_service import CandidateAdminService
from app.features.discovery.candidate_emit import DiscoveryCandidateEmitService
from app.features.discovery.candidate_service import CandidateService
from app.features.discovery.db_headroom import DB_WRITE_GUARDS
from app.features.discovery.edge_service import EdgeService
from app.features.discovery.guards import require_discovery_machine
from app.features.discovery.repository import CandidateFilter, CandidateSourceFilter, Page
from app.models.discovery import DiscoveryCandidateStatus
from app.schema.discovery.candidate_edges import CandidateEdgesRequest, CandidateEdgesResponse
from app.schema.discovery.candidate_emit import CandidateEmitPreview, CandidateEmitRequest, CandidateEmitResponse
from app.schema.discovery.candidate_sources import CandidateSourceListResponse
from app.schema.discovery.candidates import CandidateMentionsRequest, CandidateMentionsResponse
from app.schema.discovery.read import CandidateListResponse
from app.shared.paging import PageParams


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

    @get("/", sync_to_thread=True)
    def select_candidates(
        self,
        discovery_candidate_admin_service: CandidateAdminService,
        page: PageParams,
        status: DiscoveryCandidateStatus | None = Parameter(query="status", default=None),
        min_mentions: int | None = Parameter(query="min_mentions", default=None, ge=0),
    ) -> CandidateListResponse:
        """Page through candidates for workers, optionally filtered by status and minimum mentions."""
        candidate_filter = CandidateFilter(status=status, min_mentions=min_mentions)
        return discovery_candidate_admin_service.list_candidates(
            candidate_filter, Page(offset=page.offset, limit=page.limit)
        )

    @get("/sources", sync_to_thread=True)
    def select_candidate_sources(
        self,
        discovery_candidate_admin_service: CandidateAdminService,
        page: PageParams,
        missing: Literal["screenshot"] | None = Parameter(query="missing", default=None),
        host: str | None = Parameter(query="host", default=None, min_length=1, max_length=253),
        candidate_id: UUID | None = Parameter(query="candidate_id", default=None),
        service_ids: list[UUID] | None = Parameter(query="catalogue_service_id", default=None, max_items=20),
    ) -> CandidateSourceListResponse:
        """Page through procedures with candidate mentions, narrowed by missing screenshot, host or candidate."""
        candidate_filter = CandidateSourceFilter(
            missing_screenshot=missing == "screenshot",
            host=host,
            candidate_id=candidate_id,
            service_ids=service_ids or (),
        )
        return discovery_candidate_admin_service.list_candidate_sources(
            candidate_filter, Page(offset=page.offset, limit=page.limit)
        )

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
