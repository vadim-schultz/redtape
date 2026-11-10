"""The translation task queue: claim, fail, release and summary over ``translation_task``."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import settings
from app.features.discovery.task_retry import FailureKind
from app.features.search.clock import Clock, utc_now
from app.features.search.leased_queue import LeasedQueue
from app.features.search.leased_settle import fail_owned, release_owned
from app.features.search.task_settle import fail_task
from app.features.translation.repository import TranslationRepository
from app.features.translation.source import SourceRepository
from app.features.translation.unit import TranslationUnit
from app.models.translation import TranslationTask
from app.schema.translation.machine import (
    ClaimedTranslationTask,
    TranslationClaimResponse,
    TranslationFailRequest,
    TranslationFailResponse,
    TranslationReleaseResponse,
    TranslationSummaryResponse,
)

SOURCE_MISSING = "german source missing"


def _claim_item(task: TranslationTask, unit: TranslationUnit) -> ClaimedTranslationTask:
    """Return the claim item for ``task``; the task takes the hash of the unit it serves."""
    task.source_hash = unit.source_hash
    assert task.lease_expires_at is not None
    return ClaimedTranslationTask(
        task_id=task.id,
        candidate_id=task.candidate_id,
        locale=task.locale,
        title=unit.title,
        description=unit.description,
        source_hash=unit.source_hash,
        lease_expires_at=task.lease_expires_at,
    )


class TranslationQueue:
    """Lease translation tasks to a machine key and settle them when the worker gives up or hands them back."""

    def __init__(self, session: Session, clock: Clock = utc_now) -> None:
        """Bind the queue to ``session``; ``clock`` supplies the current time."""
        self._leased = LeasedQueue(session, TranslationTask)
        self._source = SourceRepository(session)
        self._index = TranslationRepository(session)
        self._clock = clock

    def claim(self, api_key_id: UUID, limit: int) -> TranslationClaimResponse:
        """Lease up to ``limit`` ready tasks of the target locales, best candidates first, with their current unit.

        A task whose candidate has lost its German title is failed, not served.
        """
        now = self._clock()
        scope = (TranslationTask.locale.in_(settings.translation_target_locale_codes),)
        tasks = self._leased.claim(api_key_id, now, limit, scope, grouping=(TranslationTask.candidate_id,))
        units = self._source.units_for(list({task.candidate_id for task in tasks}))
        return TranslationClaimResponse(items=[item for task in tasks if (item := self._serve(task, units, now))])

    def fail(self, api_key_id: UUID, request: TranslationFailRequest) -> TranslationFailResponse:
        """Record the worker's failure of a task it holds; raise :exc:`TaskNotOwnedError` for any other task."""
        kind = FailureKind.RETRYABLE if request.retryable else FailureKind.PERMANENT
        task = fail_owned(self._leased, api_key_id, request.task_id, request.error, kind, self._clock())
        return TranslationFailResponse(task_id=task.id, status=task.status, last_error=request.error)

    def release(self, api_key_id: UUID, task_ids: list[UUID], reason: str) -> TranslationReleaseResponse:
        """Hand back every listed task the key holds without consuming an attempt; report the rest as skipped."""
        released, skipped = release_owned(self._leased, api_key_id, task_ids, reason)
        return TranslationReleaseResponse(released=released, skipped=skipped)

    def summary(self) -> TranslationSummaryResponse:
        """Count the queue and the store per target locale without leasing anything."""
        return TranslationSummaryResponse(
            locales=self._index.summary(settings.translation_target_locale_codes, self._clock())
        )

    def _serve(
        self, task: TranslationTask, units: dict[UUID, TranslationUnit], now: datetime
    ) -> ClaimedTranslationTask | None:
        unit = units.get(task.candidate_id)
        if unit is None:
            fail_task(task, SOURCE_MISSING, FailureKind.PERMANENT, now)
            return None
        return _claim_item(task, unit)
