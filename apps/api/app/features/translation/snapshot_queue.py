"""The snapshot task queue: claim pages by reference, stamp the latest snapshot onto the task, fail, release and count."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import settings
from app.features.discovery.artifact_read import ArtifactReadService, LatestSnapshot
from app.features.discovery.task_retry import FailureKind
from app.features.search.clock import Clock, utc_now
from app.features.search.leased_queue import LeasedQueue
from app.features.search.leased_settle import fail_owned, release_owned
from app.features.search.task_settle import fail_task
from app.features.translation.snapshot_checks import NO_SNAPSHOT
from app.features.translation.snapshot_repository import SnapshotRepository
from app.models.snapshot_translation import SnapshotTranslationTask
from app.schema.translation.machine import TranslationFailRequest, TranslationFailResponse, TranslationReleaseResponse
from app.schema.translation.snapshot_machine import (
    ClaimedSnapshotTask,
    SnapshotClaimResponse,
    SnapshotSummaryResponse,
)


def _claim_item(task: SnapshotTranslationTask, latest: LatestSnapshot, stored_hash: str | None) -> ClaimedSnapshotTask:
    """Return the claim item for ``task``; the task takes the artifact it serves and that artifact's hash."""
    task.artifact_id, task.artifact_sha256, task.source_hash = latest.artifact_id, latest.sha256, latest.sha256
    assert task.lease_expires_at is not None
    return ClaimedSnapshotTask(
        task_id=task.id,
        catalogue_service_id=task.catalogue_service_id,
        locale=task.locale,
        artifact_id=latest.artifact_id,
        artifact_sha256=latest.sha256,
        source_url=latest.source_url,
        stored_source_hash=stored_hash,
        lease_expires_at=task.lease_expires_at,
    )


class SnapshotQueue:
    """Lease snapshot tasks to a machine key and settle them when the worker gives up or hands them back."""

    def __init__(self, session: Session, artifacts: ArtifactReadService, clock: Clock = utc_now) -> None:
        """Bind the queue to ``session``, the discovery artifact reads it stamps from and the clock."""
        self._leased = LeasedQueue(session, SnapshotTranslationTask)
        self._index = SnapshotRepository(session)
        self._artifacts = artifacts
        self._clock = clock

    def claim(self, api_key_id: UUID, limit: int) -> SnapshotClaimResponse:
        """Lease up to ``limit`` ready page tasks of the target locales, each stamped with the latest snapshot.

        A page whose catalogue row has no snapshot is failed, not served.

        Tasks are claimed in order: phase, priority, catalogue_service (grouping), created_at, id.
        This ensures breadth-first coverage (phase 1) followed by depth-first (phase 2).
        """
        now = self._clock()
        scope = (SnapshotTranslationTask.locale.in_(settings.translation_target_locale_codes),)
        tasks = self._leased.claim(
            api_key_id,
            now,
            limit,
            scope,
            grouping=(SnapshotTranslationTask.catalogue_service_id,),
            phase_field=SnapshotTranslationTask.phase,
        )
        return SnapshotClaimResponse(items=[item for task in tasks if (item := self._serve(task, now))])

    def fail(self, api_key_id: UUID, request: TranslationFailRequest) -> TranslationFailResponse:
        """Record the worker's failure of a page task it holds; raise :exc:`TaskNotOwnedError` for any other task."""
        kind = FailureKind.RETRYABLE if request.retryable else FailureKind.PERMANENT
        task = fail_owned(self._leased, api_key_id, request.task_id, request.error, kind, self._clock())
        return TranslationFailResponse(task_id=task.id, status=task.status, last_error=request.error)

    def release(self, api_key_id: UUID, task_ids: list[UUID], reason: str) -> TranslationReleaseResponse:
        """Hand back every listed page task the key holds without consuming an attempt; report the rest as skipped."""
        released, skipped = release_owned(self._leased, api_key_id, task_ids, reason)
        return TranslationReleaseResponse(released=released, skipped=skipped)

    def summary(self) -> SnapshotSummaryResponse:
        """Count the queue and the store per target locale without leasing anything."""
        locales = settings.translation_target_locale_codes
        return SnapshotSummaryResponse(locales=self._index.summary(locales, self._clock()))

    def _serve(self, task: SnapshotTranslationTask, now: datetime) -> ClaimedSnapshotTask | None:
        latest = self._artifacts.latest_snapshot(task.catalogue_service_id)
        if latest is None:
            fail_task(task, NO_SNAPSHOT, FailureKind.PERMANENT, now)
            return None
        stored_hash = self._index.stored_hash((task.catalogue_service_id, task.locale))
        return _claim_item(task, latest, stored_hash)
