"""Read-only admin HTTP handlers for artifacts."""

from __future__ import annotations

from uuid import UUID

from litestar import Controller, get

from app.features.discovery.artifact_read import ArtifactReadService
from app.features.discovery.guards import DISCOVERY_ADMIN_GUARDS
from app.features.discovery.repository import Page
from app.schema.discovery.artifacts import AdminArtifactListResponse
from app.shared.paging import PageParams


class DiscoveryArtifactAdminController(Controller):
    """Allowlisted operators download the artifacts of a catalogue row."""

    path = "/"
    guards = DISCOVERY_ADMIN_GUARDS

    @get("/catalogue/{catalogue_id:uuid}/artifacts", sync_to_thread=True)
    def catalogue_artifacts(
        self,
        discovery_artifact_read_service: ArtifactReadService,
        page: PageParams,
        catalogue_id: UUID,
    ) -> AdminArtifactListResponse:
        return discovery_artifact_read_service.list_for_catalogue(catalogue_id, Page(page.offset, page.limit))
