"""Discovery machine HTTP handlers for ingest workers and crawlers."""

from __future__ import annotations

from uuid import UUID

from litestar import Controller, Response, get, post
from litestar.params import Parameter
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED

from app.features.auth.principal import MachinePrincipal
from app.features.discovery.db_headroom import DB_WRITE_GUARDS
from app.features.discovery.emit import DiscoveryEmitService
from app.features.discovery.guards import require_discovery_machine
from app.features.discovery.repository.task_target import ExtractedText
from app.features.discovery.run_service import DiscoveryRunService
from app.features.discovery.service import DiscoveryMachineService
from app.models.discovery import DiscoveryTaskKind
from app.schema.discovery.machine import (
    TEXT_HASH_PATTERN,
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
    RunFinishRequest,
    RunRead,
    RunStartRequest,
    TaskClaimRequest,
    TaskClaimResponse,
    TaskCompleteRequest,
    TaskCompleteResponse,
    TaskEnqueueRequest,
    TaskEnqueueResponse,
    TaskFailRequest,
    TaskFailResponse,
    TaskReleaseRequest,
    TaskReleaseResponse,
    TaskRequeueRequest,
    TaskRequeueResponse,
    TaskSummaryResponse,
    TextExtractedResponse,
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
        """Return one catalogue row in the shape machine clients read it."""
        return discovery_machine_service.get_catalogue_for_machine(catalogue_id)

    @post("/catalogue/batch", sync_to_thread=True, status_code=HTTP_201_CREATED)
    def batch_catalogue(
        self,
        discovery_machine_service: DiscoveryMachineService,
        data: CatalogueBatchRequest,
    ) -> CatalogueBatchResponse:
        """Upsert a batch of catalogue rows."""
        return discovery_machine_service.batch_upsert(data)

    @post("/tasks", sync_to_thread=True, status_code=HTTP_201_CREATED, guards=DB_WRITE_GUARDS)
    def enqueue_task(
        self,
        discovery_machine_service: DiscoveryMachineService,
        data: TaskEnqueueRequest,
    ) -> Response[TaskEnqueueResponse]:
        """Enqueue a discovery task; a repeat enqueue answers 200 instead of 201."""
        result = discovery_machine_service.enqueue_task(data)
        return Response(result, status_code=HTTP_201_CREATED if result.created else HTTP_200_OK)

    @post("/tasks/claim", sync_to_thread=True, status_code=HTTP_200_OK)
    def claim_tasks(
        self,
        discovery_machine_service: DiscoveryMachineService,
        machine_principal: MachinePrincipal,
        data: TaskClaimRequest,
    ) -> TaskClaimResponse:
        """Lease pending tasks to the calling machine key for its next work."""
        return discovery_machine_service.claim_tasks(data, api_key=machine_principal.api_key)

    @get("/tasks/summary", sync_to_thread=True, status_code=HTTP_200_OK)
    def tasks_summary(
        self,
        discovery_machine_service: DiscoveryMachineService,
        kinds: list[DiscoveryTaskKind] | None = None,
    ) -> TaskSummaryResponse:
        """Count the task queue for the given kinds without leasing anything."""
        return discovery_machine_service.task_summary(kinds)

    @post("/tasks/{task_id:uuid}/complete", sync_to_thread=True)
    def complete_task(
        self,
        discovery_machine_service: DiscoveryMachineService,
        task_id: UUID,
        data: TaskCompleteRequest | None = None,
    ) -> TaskCompleteResponse:
        """Mark a claimed task complete, optionally with a completion payload."""
        return discovery_machine_service.complete_task(task_id, data)

    @post("/tasks/{task_id:uuid}/release", sync_to_thread=True, status_code=HTTP_200_OK)
    def release_task(
        self,
        discovery_machine_service: DiscoveryMachineService,
        task_id: UUID,
        data: TaskReleaseRequest,
    ) -> TaskReleaseResponse:
        """Return a claimed task to the queue so another worker can claim it."""
        return discovery_machine_service.release_task(task_id, data)

    @post("/tasks/{task_id:uuid}/fail", sync_to_thread=True)
    def fail_task(
        self,
        discovery_machine_service: DiscoveryMachineService,
        task_id: UUID,
        data: TaskFailRequest,
    ) -> TaskFailResponse:
        """Record that a claimed task failed, with the reason from the request."""
        return discovery_machine_service.fail_task(task_id, data)

    @get("/tasks/text-extracted", sync_to_thread=True, status_code=HTTP_200_OK)
    def text_extracted(
        self,
        discovery_machine_service: DiscoveryMachineService,
        catalogue_service_id: UUID,
        target_url: str = Parameter(min_length=1, max_length=500),
        input_key: str = Parameter(min_length=1, max_length=128),
        text_hash: str = Parameter(pattern=TEXT_HASH_PATTERN),
    ) -> TextExtractedResponse:
        """Report whether a completed extraction of the page under ``input_key`` already read the same cleaned text."""
        extracted = ExtractedText(
            catalogue_service_id=catalogue_service_id, target_url=target_url, input_key=input_key, text_hash=text_hash
        )
        return discovery_machine_service.text_extracted(extracted)

    @post("/tasks/requeue-transient", sync_to_thread=True, status_code=HTTP_200_OK)
    def requeue_transient_tasks(
        self,
        discovery_machine_service: DiscoveryMachineService,
        data: TaskRequeueRequest,
    ) -> TaskRequeueResponse:
        """Return failed transient tasks that are at least 24 h old to the queue; permanent failures are never touched."""
        return discovery_machine_service.requeue_transient(data)

    @post("/tasks/{task_id:uuid}/fetches", sync_to_thread=True, status_code=HTTP_201_CREATED, guards=DB_WRITE_GUARDS)
    def append_fetch_log(
        self,
        discovery_machine_service: DiscoveryMachineService,
        task_id: UUID,
        data: FetchLogAppendRequest,
    ) -> FetchLogAppendResponse:
        """Append one fetch-log entry to a task."""
        return discovery_machine_service.append_fetch_log(task_id, data)

    @post("/runs", sync_to_thread=True, status_code=HTTP_201_CREATED)
    def start_run(
        self,
        discovery_run_service: DiscoveryRunService,
        data: RunStartRequest,
    ) -> RunRead:
        """Start a discovery run for the calling machine."""
        return discovery_run_service.start(data)

    @post("/runs/{run_id:uuid}/finish", sync_to_thread=True, status_code=HTTP_200_OK)
    def finish_run(
        self,
        discovery_run_service: DiscoveryRunService,
        run_id: UUID,
        data: RunFinishRequest,
    ) -> RunRead:
        """Close a discovery run with its outcome."""
        return discovery_run_service.finish(run_id, data)

    @post("/entities", sync_to_thread=True, status_code=HTTP_201_CREATED, guards=DB_WRITE_GUARDS)
    def upsert_entity(
        self,
        discovery_machine_service: DiscoveryMachineService,
        data: EntityUpsertRequest,
    ) -> EntityUpsertResponse:
        """Create or update one entity from the request."""
        return discovery_machine_service.upsert_entity(data)

    @post("/claims", sync_to_thread=True, status_code=HTTP_201_CREATED, guards=DB_WRITE_GUARDS)
    def append_claim(
        self,
        discovery_machine_service: DiscoveryMachineService,
        data: ClaimAppendRequest,
    ) -> ClaimAppendResponse:
        """Append one claim to the staging pipeline."""
        return discovery_machine_service.append_claim(data)

    @post("/catalogue/{catalogue_id:uuid}/emit", sync_to_thread=True, status_code=HTTP_200_OK)
    def emit_catalogue(
        self,
        discovery_emit_service: DiscoveryEmitService,
        machine_principal: MachinePrincipal,
        catalogue_id: UUID,
    ) -> CatalogueEmitResponse:
        """Emit the suggestions of one catalogue row under the calling machine key."""
        return discovery_emit_service.emit_catalogue(catalogue_id, api_key=machine_principal.api_key)
