"""Discovery machine HTTP handlers for ingest workers and crawlers."""

from __future__ import annotations

from uuid import UUID

from litestar import Controller, get, post
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED

from app.features.auth.principal import MachinePrincipal
from app.features.discovery.emit import DiscoveryEmitService
from app.features.discovery.guards import require_discovery_machine
from app.features.discovery.service import DiscoveryMachineService
from app.schema.discovery.machine import (
    CatalogueBatchRequest,
    CatalogueBatchResponse,
    CatalogueEmitResponse,
    CatalogueMachineRead,
    ClaimAppendRequest,
    ClaimAppendResponse,
    EntityUpsertRequest,
    EntityUpsertResponse,
    FetchLogAppendRequest,
    FetchLogAppendResponse,
    TaskClaimRequest,
    TaskClaimResponse,
    TaskCompleteResponse,
    TaskFailRequest,
    TaskFailResponse,
)


class DiscoveryMachineController(Controller):
    """Machine clients upsert catalogue rows and claim fetch work."""

    path = "/"
    guards = [require_discovery_machine]

    @get("/catalogue/{catalogue_id:uuid}", sync_to_thread=True, status_code=HTTP_200_OK)
    def get_catalogue(
        self,
        discovery_machine_service: DiscoveryMachineService,
        catalogue_id: UUID,
    ) -> CatalogueMachineRead:
        return discovery_machine_service.get_catalogue_for_machine(catalogue_id)

    @post("/catalogue/batch", sync_to_thread=True, status_code=HTTP_201_CREATED)
    def batch_catalogue(
        self,
        discovery_machine_service: DiscoveryMachineService,
        data: CatalogueBatchRequest,
    ) -> CatalogueBatchResponse:
        return discovery_machine_service.batch_upsert(data)

    @post("/tasks/claim", sync_to_thread=True, status_code=HTTP_200_OK)
    def claim_tasks(
        self,
        discovery_machine_service: DiscoveryMachineService,
        machine_principal: MachinePrincipal,
        data: TaskClaimRequest,
    ) -> TaskClaimResponse:
        return discovery_machine_service.claim_tasks(data, api_key=machine_principal.api_key)

    @post("/tasks/{task_id:uuid}/complete", sync_to_thread=True)
    def complete_task(
        self,
        discovery_machine_service: DiscoveryMachineService,
        task_id: UUID,
    ) -> TaskCompleteResponse:
        return discovery_machine_service.complete_task(task_id)

    @post("/tasks/{task_id:uuid}/fail", sync_to_thread=True)
    def fail_task(
        self,
        discovery_machine_service: DiscoveryMachineService,
        task_id: UUID,
        data: TaskFailRequest,
    ) -> TaskFailResponse:
        return discovery_machine_service.fail_task(task_id, data)

    @post("/tasks/{task_id:uuid}/fetches", sync_to_thread=True, status_code=HTTP_201_CREATED)
    def append_fetch_log(
        self,
        discovery_machine_service: DiscoveryMachineService,
        task_id: UUID,
        data: FetchLogAppendRequest,
    ) -> FetchLogAppendResponse:
        return discovery_machine_service.append_fetch_log(task_id, data)

    @post("/entities", sync_to_thread=True, status_code=HTTP_201_CREATED)
    def upsert_entity(
        self,
        discovery_machine_service: DiscoveryMachineService,
        data: EntityUpsertRequest,
    ) -> EntityUpsertResponse:
        return discovery_machine_service.upsert_entity(data)

    @post("/claims", sync_to_thread=True, status_code=HTTP_201_CREATED)
    def append_claim(
        self,
        discovery_machine_service: DiscoveryMachineService,
        data: ClaimAppendRequest,
    ) -> ClaimAppendResponse:
        return discovery_machine_service.append_claim(data)

    @post("/catalogue/{catalogue_id:uuid}/emit", sync_to_thread=True, status_code=HTTP_200_OK)
    def emit_catalogue(
        self,
        discovery_emit_service: DiscoveryEmitService,
        machine_principal: MachinePrincipal,
        catalogue_id: UUID,
    ) -> CatalogueEmitResponse:
        return discovery_emit_service.emit_catalogue(catalogue_id, api_key=machine_principal.api_key)
