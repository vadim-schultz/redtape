"""Read-only discovery admin HTTP handlers."""

from __future__ import annotations

from uuid import UUID

from litestar import Controller, get
from litestar.di import Provide

from app.features.discovery.admin_service import DiscoveryAdminService
from app.features.discovery.catalogue_list_query import CATALOGUE_LIST_SPEC, provide_catalogue_query
from app.features.discovery.flow.service import FlowService
from app.features.discovery.guards import DISCOVERY_ADMIN_GUARDS
from app.features.discovery.list_query import DiscoveryListQuery
from app.features.discovery.repository import CatalogueFilter, TaskFilter
from app.features.discovery.task_list_query import TASK_LIST_SPEC, provide_task_query
from app.schema.discovery.flow import FlowResponse
from app.schema.discovery.read import (
    CatalogueListResponse,
    CataloguePipelineResponse,
    DiscoveryCoverageResponse,
    DiscoveryTaskListResponse,
    EmitPreviewResponse,
)
from app.shared.list_query import provide_list_query


class DiscoveryAdminController(Controller):
    """Allowlisted operators review the staging pipeline."""

    path = "/"
    guards = DISCOVERY_ADMIN_GUARDS

    @get(
        "/tasks",
        sync_to_thread=True,
        dependencies={
            "list_query": provide_list_query(TASK_LIST_SPEC),
            "discovery_query": Provide(provide_task_query, sync_to_thread=False),
        },
    )
    def list_tasks(
        self,
        discovery_admin_service: DiscoveryAdminService,
        discovery_query: DiscoveryListQuery[TaskFilter],
    ) -> DiscoveryTaskListResponse:
        """Page through discovery tasks, optionally narrowed by status, source or kind."""
        return discovery_admin_service.list_tasks(discovery_query.filters, discovery_query.page)

    @get(
        "/catalogue",
        sync_to_thread=True,
        dependencies={
            "list_query": provide_list_query(CATALOGUE_LIST_SPEC),
            "discovery_query": Provide(provide_catalogue_query, sync_to_thread=False),
        },
    )
    def list_catalogue(
        self,
        discovery_admin_service: DiscoveryAdminService,
        discovery_query: DiscoveryListQuery[CatalogueFilter],
    ) -> CatalogueListResponse:
        """Page through catalogue rows, optionally narrowed by source."""
        return discovery_admin_service.list_catalogue(discovery_query.filters, discovery_query.page)

    @get("/coverage", sync_to_thread=True)
    def coverage(self, discovery_admin_service: DiscoveryAdminService) -> DiscoveryCoverageResponse:
        """Report coverage counters across sources and the last successful run."""
        return discovery_admin_service.coverage()

    @get("/flow", sync_to_thread=True)
    def flow(self, discovery_flow_service: FlowService) -> FlowResponse:
        """Describe the pipeline: every stage with its state and last run, the edges, the allotments and the unused headroom."""
        return discovery_flow_service.flow()

    @get("/catalogue/{catalogue_id:uuid}/pipeline", sync_to_thread=True)
    def catalogue_pipeline(
        self,
        discovery_admin_service: DiscoveryAdminService,
        catalogue_id: UUID,
    ) -> CataloguePipelineResponse:
        """Show the read-only pipeline state of one catalogue row."""
        return discovery_admin_service.catalogue_pipeline(catalogue_id)

    @get("/catalogue/{catalogue_id:uuid}/emit-preview", sync_to_thread=True)
    def catalogue_emit_preview(
        self,
        discovery_admin_service: DiscoveryAdminService,
        catalogue_id: UUID,
    ) -> EmitPreviewResponse:
        """Preview the suggestions an emit of one catalogue row would create, without writing."""
        return discovery_admin_service.emit_preview(catalogue_id)
