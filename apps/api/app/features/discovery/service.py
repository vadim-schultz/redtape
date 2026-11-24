"""Machine ingest and crawler queue operations."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.features.discovery.catalogue_upsert import CatalogueUpsertService
from app.features.discovery.claim_ingest import ClaimIngest
from app.features.discovery.errors import InvalidDiscoveryInputError
from app.features.discovery.fanout import apply_fanout_for_service
from app.features.discovery.lookups import require_artifact, require_catalogue, require_task
from app.features.discovery.render_gate import NO_RENDER, RenderHistory, RenderVerdict, decide_render, refresh_key
from app.features.discovery.repository import DiscoveryRepository, FetchLogEntry, NewEvent, TaskTarget
from app.features.discovery.repository.task_target import ExtractedText
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
    StaleFetchesResponse,
    StaleFetchRead,
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
    TaskSupersededRequest,
    TaskSupersededResponse,
    TextExtractedResponse,
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
        refresh_max_age: timedelta,
    ) -> None:
        """Bind the service to ``repository`` and to the collaborators that write catalogue rows, tasks and claims."""
        self._repo = repository
        self._catalogue_upserts = catalogue_upserts
        self._queue = queue
        self._claim_ingest = claim_ingest
        self._refresh_max_age = refresh_max_age

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
        """Mark a task completed, keeping the optional note and the text hash it read."""
        request = body or TaskCompleteRequest()
        task = self._queue.complete(task_id, note=request.note, text_hash=request.text_hash)
        return TaskCompleteResponse(id=task.id, status=task.status)

    def text_extracted(self, extracted: ExtractedText) -> TextExtractedResponse:
        """Report whether a completed extraction of this page under the same input key recorded the same text hash."""
        return TextExtractedResponse(extracted=self._repo.text_extracted(extracted))

    def release_task(self, task_id: UUID, body: TaskReleaseRequest) -> TaskReleaseResponse:
        """Return a claimed task to the queue without consuming an attempt."""
        task = self._queue.release(task_id, body.reason, not_before=body.not_before)
        return TaskReleaseResponse(id=task.id, status=task.status, last_error=body.reason)

    def fail_task(self, task_id: UUID, body: TaskFailRequest) -> TaskFailResponse:
        """Mark a task failed with the crawler's error."""
        task = self._queue.fail(
            task_id, body.error, retryable=body.retryable, now=datetime.now(UTC), failure_class=body.failure_class
        )
        return TaskFailResponse(id=task.id, status=task.status, last_error=body.error)

    def requeue_transient(self, body: TaskRequeueRequest) -> TaskRequeueResponse:
        """Return transient failures that have cooled down to the queue, with a fresh attempt count."""
        return TaskRequeueResponse(requeued=self._queue.requeue_transient(limit=body.limit, now=datetime.now(UTC)))

    def requeue_superseded(self, body: TaskSupersededRequest) -> TaskSupersededResponse:
        """Re-pend completed tasks that completed under an older input key, under the current one, once per page."""
        found = self._queue.requeue_superseded(
            kind=body.kind, input_key=body.input_key, limit=body.limit, dry_run=body.dry_run
        )
        return TaskSupersededResponse(matched=found.matched, requeued=found.requeued)

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
        """Record a fetch attempt, answer whether its body earns a render, and advance the catalogue stage."""
        task = require_task(self._repo, task_id)
        previous = self._repo.last_body_sha256(
            catalogue_service_id=task.catalogue_service_id, kind=task.kind, target_url=task.target_url
        )
        row = self._repo.append_fetch_log(_fetch_log_entry(task, body))
        self._repo.record_event(_fetch_logged(task, str(row.id)))
        verdict = self._render_verdict(task, body, previous)
        self._advance_task_catalogue(task.catalogue_service_id)
        return FetchLogAppendResponse(
            id=row.id,
            discovery_task_id=task.id,
            task_status=task.status,
            render_due=verdict.due,
            render_input_key=verdict.input_key,
        )

    def stale_fetches(self, limit: int) -> StaleFetchesResponse:
        """List up to ``limit`` portal pages due a refresh, stalest first, with the week's key their refresh fetches go under."""
        now = datetime.now(UTC)
        rows = self._repo.stale_fetch_targets(cutoff=now - self._refresh_max_age, limit=limit)
        return StaleFetchesResponse(
            input_key=refresh_key(now), items=[StaleFetchRead.model_validate(asdict(row)) for row in rows]
        )

    def _render_verdict(self, task: DiscoveryTask, body: FetchLogAppendRequest, previous: str | None) -> RenderVerdict:
        """Return the render verdict for a fetched body; a fetch that read no body, or landed nowhere, asks for no render."""
        if body.body_sha256 is None or body.final_url is None:
            return NO_RENDER
        last_completed_at = self._repo.last_render_completed_at(task.catalogue_service_id, body.final_url)
        return decide_render(
            previous_sha256=previous,
            body_sha256=body.body_sha256,
            history=RenderHistory(last_completed_at=last_completed_at),
            now=datetime.now(UTC),
            max_age=self._refresh_max_age,
        )

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
        body_sha256=body.body_sha256,
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
