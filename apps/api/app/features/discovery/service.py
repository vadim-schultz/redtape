"""Discovery admin reads and machine-route orchestration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from litestar.exceptions import NotFoundException

from app.features.discovery.repository import DiscoveryRepository
from app.models.api_key import ApiKey
from app.models.discovery import (
    CatalogueService,
    DiscoveryEventType,
    DiscoverySource,
    DiscoveryTask,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)
from app.schema.discovery.machine import (
    CatalogueBatchItemResult,
    CatalogueBatchRequest,
    CatalogueBatchResponse,
    ClaimedTaskRead,
    FetchLogAppendRequest,
    FetchLogAppendResponse,
    TaskClaimRequest,
    TaskClaimResponse,
    TaskCompleteResponse,
    TaskFailRequest,
    TaskFailResponse,
)
from app.schema.discovery.read import (
    CatalogueListResponse,
    CataloguePipelineResponse,
    CatalogueServiceRead,
    CatalogueSummaryChips,
    DiscoveryTaskListResponse,
    DiscoveryTaskRead,
)

TASK_LEASE_MINUTES = 15


class DiscoveryAdminService:
    """Read-only discovery data for allowlisted operators."""

    def __init__(self, repository: DiscoveryRepository) -> None:
        self._repo = repository

    def list_tasks(
        self,
        *,
        status: DiscoveryTaskStatus | None,
        source: DiscoverySource | None,
        offset: int,
        limit: int,
    ) -> DiscoveryTaskListResponse:
        total = self._repo.count_tasks(status=status, source=source)
        rows = self._repo.list_tasks_page(offset=offset, limit=limit, status=status, source=source)
        items = [DiscoveryTaskRead.from_row(task, source=task_source) for task, task_source in rows]
        return DiscoveryTaskListResponse(items=items, total=total, offset=offset, limit=limit)

    def list_catalogue(
        self,
        *,
        source: DiscoverySource | None,
        offset: int,
        limit: int,
    ) -> CatalogueListResponse:
        total = self._repo.count_catalogue(source=source)
        rows = self._repo.list_catalogue_page(offset=offset, limit=limit, source=source)
        items = [CatalogueServiceRead.from_row(row) for row in rows]
        chip_total, by_source, by_stage = self._repo.catalogue_summary(source=source)
        summary = CatalogueSummaryChips(total=chip_total, by_source=by_source, by_pipeline_stage=by_stage)
        return CatalogueListResponse(items=items, summary=summary, total=total, offset=offset, limit=limit)

    def pipeline_stub(self, catalogue_id: UUID) -> CataloguePipelineResponse | None:
        row = self._repo.get_catalogue(catalogue_id)
        if row is None:
            return None
        return CataloguePipelineResponse(service=CatalogueServiceRead.from_row(row))


def _enqueue_tasks_for_service(
    repo: DiscoveryRepository,
    service: CatalogueService,
) -> DiscoveryTask | None:
    if not service.portal_url:
        return None
    task = repo.insert_task(
        catalogue_service_id=service.id,
        kind=DiscoveryTaskKind.FETCH_URL,
        target_url=service.portal_url,
    )
    if service.pipeline_stage == "T0":
        service.pipeline_stage = "T1"
    repo.record_event(
        event_type=DiscoveryEventType.TASK_ENQUEUED,
        catalogue_service_id=service.id,
        discovery_task_id=task.id,
        payload={"kind": task.kind.value, "target_url": task.target_url},
    )
    return task


def _claim_pending_tasks(
    repo: DiscoveryRepository,
    *,
    api_key: ApiKey,
    limit: int,
    now: datetime,
) -> list[DiscoveryTask]:
    lease_expires_at = now + timedelta(minutes=TASK_LEASE_MINUTES)
    pending = repo.list_pending_tasks_for_claim(limit=limit)
    claimed: list[DiscoveryTask] = []
    for task in pending:
        task.status = DiscoveryTaskStatus.CLAIMED
        task.claimed_at = now
        task.claimed_by_api_key_id = api_key.id
        task.lease_expires_at = lease_expires_at
        repo.record_event(
            event_type=DiscoveryEventType.TASK_CLAIMED,
            catalogue_service_id=task.catalogue_service_id,
            discovery_task_id=task.id,
            payload={"api_key_id": str(api_key.id)},
        )
        claimed.append(task)
    return claimed


class DiscoveryMachineService:
    """Machine ingest and crawler queue operations."""

    def __init__(self, repository: DiscoveryRepository) -> None:
        self._repo = repository

    def batch_upsert(self, body: CatalogueBatchRequest) -> CatalogueBatchResponse:
        results: list[CatalogueBatchItemResult] = []
        for item in body.items:
            row, _created = self._repo.upsert_catalogue_item(item)
            self._repo.record_event(
                event_type=DiscoveryEventType.CATALOGUE_UPSERTED,
                catalogue_service_id=row.id,
                payload={"source": row.source.value, "external_id": row.external_id},
            )
            task = _enqueue_tasks_for_service(self._repo, row)
            results.append(
                CatalogueBatchItemResult(
                    id=row.id,
                    source=row.source,
                    external_id=row.external_id,
                    task_id=task.id if task is not None else None,
                )
            )
        return CatalogueBatchResponse(items=results)

    def claim_tasks(self, body: TaskClaimRequest, *, api_key: ApiKey) -> TaskClaimResponse:
        now = datetime.now(UTC)
        claimed = _claim_pending_tasks(self._repo, api_key=api_key, limit=body.limit, now=now)
        items = [
            ClaimedTaskRead(
                id=task.id,
                catalogue_service_id=task.catalogue_service_id,
                kind=task.kind,
                target_url=task.target_url,
                status=task.status,
                priority=task.priority,
                lease_expires_at=task.lease_expires_at or now,
            )
            for task in claimed
        ]
        return TaskClaimResponse(items=items)

    def complete_task(self, task_id: UUID) -> TaskCompleteResponse:
        task = self._require_task(task_id)
        task.status = DiscoveryTaskStatus.COMPLETED
        task.lease_expires_at = None
        return TaskCompleteResponse(id=task.id, status=task.status)

    def fail_task(self, task_id: UUID, body: TaskFailRequest) -> TaskFailResponse:
        task = self._require_task(task_id)
        task.status = DiscoveryTaskStatus.FAILED
        task.last_error = body.error
        task.lease_expires_at = None
        return TaskFailResponse(id=task.id, status=task.status, last_error=task.last_error)

    def append_fetch_log(self, task_id: UUID, body: FetchLogAppendRequest) -> FetchLogAppendResponse:
        task = self._require_task(task_id)
        row = self._repo.append_fetch_log(
            task=task,
            http_status=body.http_status,
            content_type=body.content_type,
            byte_length=body.byte_length,
            error_message=body.error_message,
            fetched_at=datetime.now(UTC),
        )
        self._repo.record_event(
            event_type=DiscoveryEventType.FETCH_LOGGED,
            catalogue_service_id=task.catalogue_service_id,
            discovery_task_id=task.id,
            payload={"fetch_log_id": str(row.id)},
        )
        return FetchLogAppendResponse(id=row.id, discovery_task_id=task.id, task_status=task.status)

    def _require_task(self, task_id: UUID) -> DiscoveryTask:
        task = self._repo.get_task(task_id)
        if task is None:
            raise NotFoundException("Discovery task not found")
        return task
