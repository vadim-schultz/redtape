"""Discovery machine HTTP handlers for ingest workers and crawlers."""

from __future__ import annotations

from uuid import UUID

from litestar import Controller, post
from litestar.status_codes import HTTP_201_CREATED

from app.features.auth.principal import MachinePrincipal
from app.features.discovery.guards import require_discovery_machine
from app.features.discovery.service import DiscoveryMachineService
from app.schema.discovery.machine import (
    CatalogueBatchRequest,
    CatalogueBatchResponse,
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

    @post("/catalogue/batch", sync_to_thread=True, status_code=HTTP_201_CREATED)
    def batch_catalogue(
        self,
        discovery_machine_service: DiscoveryMachineService,
        data: CatalogueBatchRequest,
    ) -> CatalogueBatchResponse:
        return discovery_machine_service.batch_upsert(data)

    @post("/tasks/claim", sync_to_thread=True)
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
