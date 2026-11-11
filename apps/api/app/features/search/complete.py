"""Completing embedding tasks: per-item validation, the stale check and the vector write."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Final
from uuid import UUID

from sqlalchemy.orm import Session

from app.features.discovery.task_retry import FailureKind
from app.features.search.clock import Clock, utc_now
from app.features.search.embedding_repository import EmbeddingRepository
from app.features.search.enqueue import EmbeddingEnqueuer
from app.features.search.leased_queue import LeasedQueue
from app.features.search.task_settle import complete_task, fail_task
from app.features.search.text import BuiltText
from app.models.search import EMBEDDING_DIM, EmbeddingTask
from app.schema.search.machine import EmbeddingCompleteItem, EmbeddingItemResult, EmbeddingOutcome

NOT_OWNED = "task is not claimed by this key"


def _model_problem(task: EmbeddingTask, item: EmbeddingCompleteItem) -> str | None:
    if item.model == task.model:
        return None
    return f"model {item.model!r} is not the task's model {task.model!r}"


def _dimension_problem(_: EmbeddingTask, item: EmbeddingCompleteItem) -> str | None:
    if len(item.vector) == EMBEDDING_DIM:
        return None
    return f"dimension {len(item.vector)} is not {EMBEDDING_DIM}"


def _finite_problem(_: EmbeddingTask, item: EmbeddingCompleteItem) -> str | None:
    if all(math.isfinite(value) for value in item.vector):
        return None
    return "vector holds a value that is not finite"


VECTOR_CHECKS: Final = (_model_problem, _dimension_problem, _finite_problem)
"""The checks of a posted vector, in the order they run; the first problem found is the one reported."""


def vector_problem(task: EmbeddingTask, item: EmbeddingCompleteItem) -> str | None:
    """Return why the vector of ``item`` cannot be stored for ``task`` (model, width, finite values), or ``None``."""
    return next((problem for check in VECTOR_CHECKS if (problem := check(task, item))), None)


def _result(task_id: UUID, outcome: EmbeddingOutcome, reason: str | None = None) -> EmbeddingItemResult:
    return EmbeddingItemResult(task_id=task_id, outcome=outcome, reason=reason)


class EmbeddingCompletion:
    """Settle the vectors a worker posts: store the current ones, discard stale ones and refuse invalid ones."""

    def __init__(self, session: Session, clock: Clock = utc_now) -> None:
        """Bind the completion to ``session``; ``clock`` supplies the current time."""
        self._session = session
        self._leased = LeasedQueue(session, EmbeddingTask)
        self._repo = EmbeddingRepository(session)
        self._clock = clock

    def complete(self, api_key_id: UUID, items: Sequence[EmbeddingCompleteItem]) -> list[EmbeddingItemResult]:
        """Return one result per item, in order; one item that is stale or invalid never affects the others."""
        results = [self._complete_one(api_key_id, item) for item in items]
        self._session.flush()
        return results

    def _complete_one(self, api_key_id: UUID, item: EmbeddingCompleteItem) -> EmbeddingItemResult:
        task = self._leased.owned(item.task_id, api_key_id)
        if task is None:
            return _result(item.task_id, EmbeddingOutcome.REJECTED, NOT_OWNED)
        problem = vector_problem(task, item)
        if problem is not None:
            fail_task(task, problem, FailureKind.PERMANENT, self._clock())
            return _result(task.id, EmbeddingOutcome.REJECTED, problem)
        return self._store_or_discard(task, item)

    def _store_or_discard(self, task: EmbeddingTask, item: EmbeddingCompleteItem) -> EmbeddingItemResult:
        current = self._repo.locked_text(task.candidate_id, task.locale)
        complete_task(task)
        if current is not None and item.text_hash == task.text_hash == current.content_hash:
            self._repo.store_embedding(task, item.vector)
            return _result(task.id, EmbeddingOutcome.STORED)
        self._requeue(task, current)
        return _result(task.id, EmbeddingOutcome.STALE)

    def _requeue(self, task: EmbeddingTask, current: BuiltText | None) -> None:
        if current is None:
            return
        self._session.flush()
        EmbeddingEnqueuer(self._session, task.model).enqueue(task.candidate_id, current)
