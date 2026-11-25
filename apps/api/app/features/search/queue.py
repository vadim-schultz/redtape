"""The embedding task queue: claim, fail, release and summary over ``embedding_task``."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import settings
from app.features.discovery.task_retry import FailureKind
from app.features.search.clock import Clock, utc_now
from app.features.search.embedding_repository import EmbeddingRepository, TextKey
from app.features.search.leased_queue import LeasedQueue
from app.features.search.leased_settle import fail_owned, release_owned
from app.features.search.task_settle import fail_task
from app.features.search.text import BuiltText
from app.models.search import EmbeddingTask
from app.schema.search.machine import (
    ClaimedEmbeddingTask,
    EmbeddingClaimResponse,
    EmbeddingFailRequest,
    EmbeddingFailResponse,
    EmbeddingReleaseResponse,
    EmbeddingSummaryResponse,
)

TEXT_MISSING = "search text missing"


def _claim_item(task: EmbeddingTask, text: BuiltText) -> ClaimedEmbeddingTask:
    """Return the claim item for ``task``; the task takes the hash of the text it serves."""
    task.text_hash = text.content_hash
    assert task.lease_expires_at is not None
    return ClaimedEmbeddingTask(
        task_id=task.id,
        candidate_id=task.candidate_id,
        locale=task.locale,
        text=text.text,
        text_hash=text.content_hash,
        lease_expires_at=task.lease_expires_at,
    )


class EmbeddingQueue:
    """Lease embedding tasks to a machine key and settle them when the worker gives up or hands them back."""

    def __init__(self, session: Session, clock: Clock = utc_now) -> None:
        """Bind the queue to ``session``; ``clock`` supplies the current time."""
        self._leased = LeasedQueue(session, EmbeddingTask)
        self._repo = EmbeddingRepository(session)
        self._clock = clock

    def claim(self, api_key_id: UUID, model: str, limit: int) -> EmbeddingClaimResponse:
        """Lease up to ``limit`` ready tasks of ``model`` with their current text; a task with no text is failed.

        Tasks are claimed in order: phase, priority, candidate (grouping), created_at, id.
        This ensures breadth-first coverage (phase 1) followed by depth-first (phase 2).
        """
        now = self._clock()
        tasks = self._leased.claim(
            api_key_id,
            now,
            limit,
            scope=(EmbeddingTask.model == model,),
            grouping=(EmbeddingTask.candidate_id,),
            phase_field=EmbeddingTask.phase,
        )
        texts = self._repo.texts_for(tasks)
        return EmbeddingClaimResponse(items=[item for task in tasks if (item := self._serve(task, texts, now))])

    def fail(self, api_key_id: UUID, request: EmbeddingFailRequest) -> EmbeddingFailResponse:
        """Record the worker's failure of a task it holds; raise :exc:`TaskNotOwnedError` for any other task."""
        kind = FailureKind.RETRYABLE if request.retryable else FailureKind.PERMANENT
        task = fail_owned(self._leased, api_key_id, request.task_id, request.error, kind, self._clock())
        return EmbeddingFailResponse(task_id=task.id, status=task.status, last_error=request.error)

    def release(self, api_key_id: UUID, task_ids: list[UUID], reason: str) -> EmbeddingReleaseResponse:
        """Hand back every listed task the key holds without consuming an attempt; report the rest as skipped."""
        released, skipped = release_owned(self._leased, api_key_id, task_ids, reason)
        return EmbeddingReleaseResponse(released=released, skipped=skipped)

    def summary(self, model: str | None = None) -> EmbeddingSummaryResponse:
        """Count the queue of ``model`` (the configured one by default) without leasing anything."""
        return self._repo.summary(model or settings.embedding_model, self._clock())

    def _serve(
        self, task: EmbeddingTask, texts: dict[TextKey, BuiltText], now: datetime
    ) -> ClaimedEmbeddingTask | None:
        text = texts.get((task.candidate_id, task.locale))
        if text is None:
            fail_task(task, TEXT_MISSING, FailureKind.PERMANENT, now)
            return None
        return _claim_item(task, text)
