"""Read-only discovery admin HTTP handlers."""

from __future__ import annotations

from uuid import UUID

from litestar import Controller, get
from litestar.params import Parameter

from app.features.discovery.admin_service import DiscoveryAdminService
from app.features.discovery.catalogue_list_query import CATALOGUE_LIST_SPEC, catalogue_filter_from
from app.features.discovery.guards import DISCOVERY_ADMIN_GUARDS
from app.features.discovery.repository import CatalogueFilter, Page, TaskFilter
from app.features.discovery.task_list_query import TASK_LIST_SPEC, task_filter_from
from app.models.discovery import DiscoverySource, DiscoveryTaskKind, DiscoveryTaskStatus
from app.schema.discovery.read import (
    CatalogueListResponse,
    CataloguePipelineResponse,
    DiscoveryCoverageResponse,
    DiscoveryTaskListResponse,
    EmitPreviewResponse,
)
from app.shared.list_query import ListQuery, provide_list_query
from app.shared.paging import PageParams


class DiscoveryAdminController(Controller):
    """Allowlisted operators review the staging pipeline."""

    path = "/"
    guards = DISCOVERY_ADMIN_GUARDS

    @get("/tasks", sync_to_thread=True, dependencies={"list_query": provide_list_query(TASK_LIST_SPEC)})
    def list_tasks(
        self,
        discovery_admin_service: DiscoveryAdminService,
        page: PageParams,
        list_query: ListQuery,
        status: DiscoveryTaskStatus | None = Parameter(query="status", default=None),
        source: DiscoverySource | None = Parameter(query="source", default=None),
        kind: DiscoveryTaskKind | None = Parameter(query="kind", default=None),
    ) -> DiscoveryTaskListResponse:
        task_filter = task_filter_from(list_query, TaskFilter(status=status, source=source, kind=kind))
        return discovery_admin_service.list_tasks(task_filter, Page(offset=page.offset, limit=page.limit))

    @get("/catalogue", sync_to_thread=True, dependencies={"list_query": provide_list_query(CATALOGUE_LIST_SPEC)})
    def list_catalogue(
        self,
        discovery_admin_service: DiscoveryAdminService,
        page: PageParams,
        list_query: ListQuery,
        source: DiscoverySource | None = Parameter(query="source", default=None),
    ) -> CatalogueListResponse:
        catalogue_filter = catalogue_filter_from(list_query, CatalogueFilter(source=source))
        return discovery_admin_service.list_catalogue(catalogue_filter, Page(offset=page.offset, limit=page.limit))

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
