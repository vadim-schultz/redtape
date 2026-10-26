"""Machine HTTP handlers for document candidates."""

from __future__ import annotations

from uuid import UUID

from litestar import Controller, get, post
from litestar.params import Parameter
from litestar.status_codes import HTTP_200_OK

from app.features.auth.principal import MachinePrincipal
from app.features.discovery.candidate_admin_service import CandidateAdminService
from app.features.discovery.candidate_emit import DiscoveryCandidateEmitService
from app.features.discovery.candidate_service import CandidateService
from app.features.discovery.db_headroom import DB_WRITE_GUARDS
from app.features.discovery.guards import require_discovery_machine
from app.features.discovery.repository import CandidateFilter, Page
from app.models.discovery import DiscoveryCandidateStatus
from app.schema.discovery.candidate_emit import CandidateEmitPreview, CandidateEmitRequest, CandidateEmitResponse
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
        return discovery_candidate_service.record_mentions(data)

    @get("/", sync_to_thread=True)
    def select_candidates(
        self,
        discovery_candidate_admin_service: CandidateAdminService,
        page: PageParams,
        status: DiscoveryCandidateStatus | None = Parameter(query="status", default=None),
        min_mentions: int | None = Parameter(query="min_mentions", default=None, ge=0),
    ) -> CandidateListResponse:
        candidate_filter = CandidateFilter(status=status, min_mentions=min_mentions)
        return discovery_candidate_admin_service.list_candidates(
            candidate_filter, Page(offset=page.offset, limit=page.limit)
        )

    @get("/{candidate_id:uuid}/emit-preview", sync_to_thread=True)
    def preview_emit(
        self,
        discovery_candidate_emit_service: DiscoveryCandidateEmitService,
        candidate_id: UUID,
    ) -> CandidateEmitPreview:
        return discovery_candidate_emit_service.preview(candidate_id)

    @post("/emit", sync_to_thread=True, status_code=HTTP_200_OK)
    def emit_candidates(
        self,
        discovery_candidate_emit_service: DiscoveryCandidateEmitService,
        machine_principal: MachinePrincipal,
        data: CandidateEmitRequest,
    ) -> CandidateEmitResponse:
        return discovery_candidate_emit_service.emit_batch(data.candidate_ids, machine_principal.api_key)
