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
from app.models.snapshot_translation import SnapshotTranslationTask
from app.models.translation import TranslationTask

TaskT = TypeVar("TaskT", EmbeddingTask, TranslationTask, SnapshotTranslationTask)


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
        phase_field: InstrumentedAttribute[int] | None = None,
    ) -> list[TaskT]:
        """Reclaim expired leases, then lease up to ``limit`` ready tasks matching ``scope`` to ``api_key_id``.

        Tasks are ordered by:
        1. phase (if phase_field provided)
        2. priority
        3. grouping (columns whose equal values must stay together, such as the
           candidate of per-locale tasks)
        4. created_at
        5. id

        The order is stable for every claimer.

        Args:
            api_key_id: Worker identifier claiming the lease.
            now: Current timestamp for expiry checks.
            limit: Maximum tasks to claim.
            scope: WHERE clause predicates to filter tasks.
            grouping: Columns that must stay together (e.g., [task.candidate_id]).
            phase_field: Column to sort by before priority (e.g., task.phase).
        """
        self.reclaim_expired(now)
        model = self._model
        order_clauses: list[ColumnElement] = []

        # Phase first (if provided)
        if phase_field is not None:
            order_clauses.append(phase_field.expression)

        # Priority always comes next
        order_clauses.append(model.priority.expression)

        # Grouping fields (if provided)
        order_clauses.extend(column.expression for column in grouping)

        # Age and id as final tie-breakers
        order_clauses.extend([model.created_at.expression, model.id.expression])

        stmt = (
            select(model)
            .where(*ready_clause(model, now), *scope)
            .order_by(*order_clauses)
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
