"""Read-only discovery admin HTTP handlers."""

from __future__ import annotations

from uuid import UUID

from litestar import Controller, get
from litestar.params import Parameter

from app.features.discovery.guards import DISCOVERY_ADMIN_GUARDS
from app.features.discovery.service import DiscoveryAdminService
from app.models.discovery import DiscoverySource, DiscoveryTaskStatus
from app.schema.discovery.read import (
    CatalogueListResponse,
    CataloguePipelineResponse,
    DiscoveryCoverageResponse,
    DiscoveryTaskListResponse,
    EmitPreviewResponse,
)


class DiscoveryAdminController(Controller):
    """Allowlisted operators review the staging pipeline."""

    path = "/"
    guards = DISCOVERY_ADMIN_GUARDS

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

    @get("/coverage", sync_to_thread=True)
    def coverage(self, discovery_admin_service: DiscoveryAdminService) -> DiscoveryCoverageResponse:
        return discovery_admin_service.coverage()

    @get("/catalogue/{catalogue_id:uuid}/pipeline", sync_to_thread=True)
    def catalogue_pipeline(
        self,
        discovery_admin_service: DiscoveryAdminService,
        catalogue_id: UUID,
    ) -> CataloguePipelineResponse:
        return discovery_admin_service.catalogue_pipeline(catalogue_id)

    @get("/catalogue/{catalogue_id:uuid}/emit-preview", sync_to_thread=True)
    def catalogue_emit_preview(
        self,
        discovery_admin_service: DiscoveryAdminService,
        catalogue_id: UUID,
    ) -> EmitPreviewResponse:
        return discovery_admin_service.emit_preview(catalogue_id)
