"""Read-only discovery admin HTTP handlers."""

from __future__ import annotations

from uuid import UUID

from litestar import Controller, get
from litestar.exceptions import NotFoundException
from litestar.params import Parameter

from app.features.discovery.guards import require_discovery_admin
from app.features.discovery.service import DiscoveryAdminService
from app.models.discovery import DiscoverySource, DiscoveryTaskStatus
from app.schema.discovery.read import CatalogueListResponse, CataloguePipelineResponse, DiscoveryTaskListResponse


class DiscoveryAdminController(Controller):
    """Allowlisted operators review the staging pipeline."""

    path = "/"
    guards = [require_discovery_admin]

    @get("/tasks", sync_to_thread=True)
    def list_tasks(
        self,
        discovery_admin_service: DiscoveryAdminService,
        status: DiscoveryTaskStatus | None = Parameter(query="status", default=None),
        source: DiscoverySource | None = Parameter(query="source", default=None),
        offset: int = Parameter(query="offset", default=0, ge=0),
        limit: int = Parameter(query="limit", default=20, ge=1, le=100),
    ) -> DiscoveryTaskListResponse:
        return discovery_admin_service.list_tasks(status=status, source=source, offset=offset, limit=limit)

    @get("/catalogue", sync_to_thread=True)
    def list_catalogue(
        self,
        discovery_admin_service: DiscoveryAdminService,
        source: DiscoverySource | None = Parameter(query="source", default=None),
        offset: int = Parameter(query="offset", default=0, ge=0),
        limit: int = Parameter(query="limit", default=20, ge=1, le=100),
    ) -> CatalogueListResponse:
        return discovery_admin_service.list_catalogue(source=source, offset=offset, limit=limit)

    @get("/catalogue/{catalogue_id:uuid}/pipeline", sync_to_thread=True)
    def catalogue_pipeline(
        self,
        discovery_admin_service: DiscoveryAdminService,
        catalogue_id: UUID,
    ) -> CataloguePipelineResponse:
        aggregate = discovery_admin_service.pipeline_stub(catalogue_id)
        if aggregate is None:
            raise NotFoundException("Catalogue service not found")
        return aggregate
