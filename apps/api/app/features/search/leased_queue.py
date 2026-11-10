"""Claim and reclaim of leased work tasks with row locks; one implementation for every work-task table."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import ColumnElement, func, or_, select, update
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.features.discovery.task_retry import MAX_ATTEMPTS
from app.features.search.task_settle import lease_task
from app.models.search import EmbeddingTask, WorkTaskStatus
from app.models.translation import TranslationTask

TaskT = TypeVar("TaskT", EmbeddingTask, TranslationTask)


def ready_clause(model: type[TaskT], now: datetime) -> tuple[ColumnElement[bool], ...]:
    """Return the predicates that make a task of ``model`` leasable at ``now``: pending and past its ``not_before``."""
    return (model.status == WorkTaskStatus.PENDING, or_(model.not_before.is_(None), model.not_before <= now))


def _expired_clause(model: type[TaskT], now: datetime) -> tuple[ColumnElement[bool], ...]:
    return (
        model.status == WorkTaskStatus.CLAIMED,
        model.lease_expires_at.is_not(None),
        model.lease_expires_at < now,
    )


class LeasedQueue(Generic[TaskT]):
    """Lease tasks of ``model`` to a key with ``FOR UPDATE SKIP LOCKED`` and take back leases that expired.

    Claimers in separate transactions never receive the same row: a row another claim has locked is skipped, not
    waited for. Every state move goes through :mod:`app.features.search.task_settle`.
    """

    def __init__(self, session: Session, model: type[TaskT]) -> None:
        """Bind the queue to ``session`` and the task table ``model``."""
        self._session = session
        self._model: type[TaskT] = model

    def claim(
        self,
        api_key_id: UUID,
        now: datetime,
        limit: int,
        scope: Sequence[ColumnElement[bool]],
        grouping: Sequence[InstrumentedAttribute[UUID]] = (),
    ) -> list[TaskT]:
        """Reclaim expired leases, then lease up to ``limit`` ready tasks matching ``scope`` to ``api_key_id``.

        Tasks come out by priority, then ``grouping`` (columns whose equal values must stay together, such as the
        candidate of per-locale tasks), then age, then id, so the order is stable for every claimer.
        """
        self.reclaim_expired(now)
        model = self._model
        stmt = (
            select(model)
            .where(*ready_clause(model, now), *scope)
            .order_by(model.priority, *grouping, model.created_at, model.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
            .execution_options(populate_existing=True)
        )
        tasks = list(self._session.scalars(stmt))
        for task in tasks:
            lease_task(task, api_key_id, now)
        return tasks

    def owned(self, task_id: UUID, api_key_id: UUID) -> TaskT | None:
        """Lock and return the task when it is claimed by ``api_key_id``; ``None`` for an unknown or foreign task.

        The row lock fences a settle step against a concurrent reclaim: only one of them acts on the claim.
        """
        model = self._model
        self._session.flush()
        stmt = (
            select(model)
            .where(
                model.id == task_id, model.status == WorkTaskStatus.CLAIMED, model.claimed_by_api_key_id == api_key_id
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return self._session.scalars(stmt).first()

    def reclaim_expired(self, now: datetime) -> None:
        """Fail expired leases that used every attempt; return the others to the pending queue.

        These two bulk updates are the one place a task leaves ``claimed`` outside :mod:`task_settle`; they follow
        the same table (``claimed`` to ``failed`` or ``pending``).
        """
        self._session.flush()
        self._fail_exhausted(now)
        self._repend_expired(now)

    def _fail_exhausted(self, now: datetime) -> None:
        model = self._model
        message = func.concat("lease expired after ", model.attempt_count, " attempts")
        self._session.execute(
            update(model)
            .where(*_expired_clause(model, now), model.attempt_count >= MAX_ATTEMPTS)
            .values(status=WorkTaskStatus.FAILED, last_error=message, lease_expires_at=None)
        )

    def _repend_expired(self, now: datetime) -> None:
        model = self._model
        self._session.execute(
            update(model)
            .where(*_expired_clause(model, now))
            .values(status=WorkTaskStatus.PENDING, claimed_by_api_key_id=None, claimed_at=None, lease_expires_at=None)
        )
