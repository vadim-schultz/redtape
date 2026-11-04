"""Machine ingest and crawler queue operations."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, datetime
from uuid import UUID

from app.features.discovery.catalogue_upsert import CatalogueUpsertService
from app.features.discovery.claim_ingest import ClaimIngest
from app.features.discovery.errors import InvalidDiscoveryInputError
from app.features.discovery.fanout import apply_fanout_for_service
from app.features.discovery.lookups import require_artifact, require_catalogue, require_task
from app.features.discovery.repository import DiscoveryRepository, FetchLogEntry, NewEvent, TaskTarget
from app.features.discovery.stage_sync import advance_stage
from app.features.discovery.task_queue import TaskQueue
from app.features.discovery.url_normalize import normalize_canonical_url
from app.models.api_key import ApiKey
from app.models.discovery import (
    CatalogueService,
    DiscoveryEventType,
    DiscoveryTask,
    DiscoveryTaskKind,
)
from app.schema.discovery.machine import (
    CatalogueBatchItem,
    CatalogueBatchItemResult,
    CatalogueBatchRequest,
    CatalogueBatchResponse,
    CatalogueMachineRead,
    ClaimAppendRequest,
    ClaimAppendResponse,
    ClaimedTaskRead,
    EntityUpsertRequest,
    EntityUpsertResponse,
    FetchLogAppendRequest,
    FetchLogAppendResponse,
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
    TaskSummaryResponse,
    resolve_task_kinds,
)


def _claimed_task_read(task: DiscoveryTask, now: datetime) -> ClaimedTaskRead:
    return ClaimedTaskRead(
        id=task.id,
        catalogue_service_id=task.catalogue_service_id,
        kind=task.kind,
        target_url=task.target_url,
        status=task.status,
        priority=task.priority,
        lease_expires_at=task.lease_expires_at or now,
        artifact_id=task.artifact_id,
        input_key=task.input_key,
    )


def _enqueue_target(body: TaskEnqueueRequest) -> TaskTarget:
    return TaskTarget(
        catalogue_service_id=body.catalogue_service_id,
        kind=body.kind,
        target_url=body.target_url,
        input_key=body.input_key,
        artifact_id=body.artifact_id,
    )


def _batch_item_result(row: CatalogueService, task: DiscoveryTask | None) -> CatalogueBatchItemResult:
    return CatalogueBatchItemResult(
        id=row.id,
        source=row.source,
        external_id=row.external_id,
        task_id=task.id if task is not None else None,
    )


def _normalised_url(raw: str) -> str:
    try:
        return normalize_canonical_url(raw)
    except ValueError as err:
        raise InvalidDiscoveryInputError(str(err)) from err


class DiscoveryMachineService:
    """Machine ingest and crawler queue operations."""

    def __init__(
        self,
        repository: DiscoveryRepository,
        catalogue_upserts: CatalogueUpsertService,
        queue: TaskQueue,
        claim_ingest: ClaimIngest,
    ) -> None:
        """Bind the service to ``repository`` and to the collaborators that write catalogue rows, tasks and claims."""
        self._repo = repository
        self._catalogue_upserts = catalogue_upserts
        self._queue = queue
        self._claim_ingest = claim_ingest

    def batch_upsert(self, body: CatalogueBatchRequest) -> CatalogueBatchResponse:
        """Upsert catalogue rows, enqueue their tasks and fan out."""
        return CatalogueBatchResponse(items=[self._upsert_item(item) for item in body.items])

    def get_catalogue_for_machine(self, catalogue_id: UUID) -> CatalogueMachineRead:
        """Return the machine view of one catalogue row."""
        row = require_catalogue(self._repo, catalogue_id)
        return CatalogueMachineRead(
            id=row.id,
            source=row.source,
            portal_url=row.portal_url,
            title_i18n=row.title_i18n,
            raw_payload=row.raw_payload,
        )

    def claim_tasks(self, body: TaskClaimRequest, *, api_key: ApiKey) -> TaskClaimResponse:
        """Lease pending tasks to the calling key."""
        now = datetime.now(UTC)
        claimed = self._queue.claim_pending(api_key=api_key, limit=body.limit, now=now, kinds=body.resolved_kinds)
        return TaskClaimResponse(items=[_claimed_task_read(task, now) for task in claimed])

    def task_summary(self, kinds: Sequence[DiscoveryTaskKind] | None) -> TaskSummaryResponse:
        """Count the queue for ``kinds`` (the legacy kinds when none are named) without leasing."""
        summary = self._repo.task_summary(kinds=resolve_task_kinds(kinds), now=datetime.now(UTC))
        return TaskSummaryResponse.model_validate(asdict(summary))

    def enqueue_task(self, body: TaskEnqueueRequest) -> TaskEnqueueResponse:
        """Enqueue a follow-up task idempotently for an existing catalogue row."""
        require_catalogue(self._repo, body.catalogue_service_id)
        self._require_own_artifact(body)
        outcome = self._queue.enqueue(_enqueue_target(body), priority=body.priority)
        return TaskEnqueueResponse(id=outcome.task.id, created=outcome.created)

    def complete_task(self, task_id: UUID, body: TaskCompleteRequest | None = None) -> TaskCompleteResponse:
        """Mark a task completed, keeping the optional note."""
        task = self._queue.complete(task_id, note=body.note if body is not None else None)
        return TaskCompleteResponse(id=task.id, status=task.status)

    def release_task(self, task_id: UUID, body: TaskReleaseRequest) -> TaskReleaseResponse:
        """Return a claimed task to the queue without consuming an attempt."""
        task = self._queue.release(task_id, body.reason, not_before=body.not_before)
        return TaskReleaseResponse(id=task.id, status=task.status, last_error=body.reason)

    def fail_task(self, task_id: UUID, body: TaskFailRequest) -> TaskFailResponse:
        """Mark a task failed with the crawler's error."""
        task = self._queue.fail(task_id, body.error, retryable=body.retryable, now=datetime.now(UTC))
        return TaskFailResponse(id=task.id, status=task.status, last_error=body.error)

    def upsert_entity(self, body: EntityUpsertRequest) -> EntityUpsertResponse:
        """Upsert a discovery entity under a catalogue row."""
        require_catalogue(self._repo, body.catalogue_service_id)
        row, created = self._repo.upsert_entity(
            catalogue_service_id=body.catalogue_service_id,
            canonical_url=_normalised_url(body.canonical_url),
            label=body.label,
        )
        return EntityUpsertResponse(
            id=row.id,
            catalogue_service_id=row.catalogue_service_id,
            canonical_url=row.canonical_url,
            created=created,
        )

    def append_claim(self, body: ClaimAppendRequest) -> ClaimAppendResponse:
        """Append a claim to an entity."""
        return self._claim_ingest.append(body)

    def append_fetch_log(self, task_id: UUID, body: FetchLogAppendRequest) -> FetchLogAppendResponse:
        """Record a fetch attempt and advance the catalogue stage."""
        task = require_task(self._repo, task_id)
        row = self._repo.append_fetch_log(_fetch_log_entry(task, body))
        self._repo.record_event(_fetch_logged(task, str(row.id)))
        self._advance_task_catalogue(task.catalogue_service_id)
        return FetchLogAppendResponse(id=row.id, discovery_task_id=task.id, task_status=task.status)

    def _require_own_artifact(self, body: TaskEnqueueRequest) -> None:
        if body.artifact_id is None:
            return
        if require_artifact(self._repo, body.artifact_id).catalogue_service_id != body.catalogue_service_id:
            raise InvalidDiscoveryInputError("Artifact belongs to another catalogue row")

    def _upsert_item(self, item: CatalogueBatchItem) -> CatalogueBatchItemResult:
        row, _created = self._catalogue_upserts.upsert(item)
        self._repo.record_event(_catalogue_upserted(row))
        task = self._queue.enqueue_for_service(row)
        apply_fanout_for_service(self._repo, row)
        return _batch_item_result(row, task)

    def _advance_task_catalogue(self, catalogue_id: UUID) -> None:
        catalogue = self._repo.get_catalogue(catalogue_id)
        if catalogue is not None:
            advance_stage(self._repo, catalogue)


def _fetch_log_entry(task: DiscoveryTask, body: FetchLogAppendRequest) -> FetchLogEntry:
    return FetchLogEntry(
        discovery_task_id=task.id,
        http_status=body.http_status,
        content_type=body.content_type,
        byte_length=body.byte_length,
        error_message=body.error_message,
        fetched_at=datetime.now(UTC),
    )


def _fetch_logged(task: DiscoveryTask, fetch_log_id: str) -> NewEvent:
    return NewEvent(
        event_type=DiscoveryEventType.FETCH_LOGGED,
        catalogue_service_id=task.catalogue_service_id,
        discovery_task_id=task.id,
        payload={"fetch_log_id": fetch_log_id},
    )


def _catalogue_upserted(row: CatalogueService) -> NewEvent:
    return NewEvent(
        event_type=DiscoveryEventType.CATALOGUE_UPSERTED,
        catalogue_service_id=row.id,
        payload={"source": row.source.value, "external_id": row.external_id},
    )
