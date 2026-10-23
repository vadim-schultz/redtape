"""Machine HTTP handlers for document candidates."""

from __future__ import annotations

from litestar import Controller, post
from litestar.status_codes import HTTP_200_OK

from app.features.discovery.candidate_service import CandidateService
from app.features.discovery.guards import require_discovery_machine
from app.schema.discovery.candidates import CandidateMentionsRequest, CandidateMentionsResponse


class DiscoveryCandidateMachineController(Controller):
    """Workers report where documents are mentioned."""

    path = "/candidates"
    guards = [require_discovery_machine]

    @post("/mentions", sync_to_thread=True, status_code=HTTP_200_OK)
    def record_mentions(
        self,
        discovery_candidate_service: CandidateService,
        data: CandidateMentionsRequest,
    ) -> CandidateMentionsResponse:
        return discovery_candidate_service.record_mentions(data)
