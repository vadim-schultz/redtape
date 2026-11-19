"""Discovery task queue queries."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, exists, func, select

from app.features.discovery.repository.base import SessionRepository
from app.features.discovery.repository.task_clauses import (
    claimable,
    fail_exhausted_stmt,
    repend_expired_stmt,
    requeue_transient_stmt,
)
from app.features.discovery.repository.task_page_completeness import page_completeness_subquery
from app.features.discovery.repository.task_target import ExtractedText, TaskTarget, identity_clauses
from app.models.discovery import (
    DiscoveryTask,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)

# Admin/general task listing order (task_sort.py): priority, then created_at, then id. Unaffected by
# page completeness — that heuristic is claim-order-only, see ``_claim_order`` below.
QUEUE_ORDER = (DiscoveryTask.priority.asc(), DiscoveryTask.created_at.asc(), DiscoveryTask.id.asc())


def _claim_order(page_completeness: ColumnElement) -> tuple[ColumnElement, ...]:
    """Return the claim order: priority, then page-completeness-desc, then created_at, then id.

    This supersedes ``discovery-operations`` decision D7's ordering clause (D5): within a priority tier,
    the created-time tie-break now runs after a page-completeness-desc tie-break, so a page one chip from
    done claims ahead of an older, emptier page of the same priority. D7's other guarantees — the 1-50
    claim limit, 15-minute lease, reclaim-on-claim, idempotent catalogue upsert, fingerprint dedup — are
    unaffected; only this ordering changes.
    """
    return (
        DiscoveryTask.priority.asc(),
        func.coalesce(page_completeness, 0).desc(),
        DiscoveryTask.created_at.asc(),
        DiscoveryTask.id.asc(),
    )


class TaskRepository(SessionRepository):
    """Read and write the discovery task queue."""

    def find_task_for_target(
        self, target: TaskTarget, *, statuses: tuple[DiscoveryTaskStatus, ...]
    ) -> DiscoveryTask | None:
        """Return a task for ``target`` whose status is one of ``statuses``; an artifact in ``target`` narrows the match."""
        stmt = select(DiscoveryTask).where(*identity_clauses(target), DiscoveryTask.status.in_(statuses)).limit(1)
        return self._session.scalar(stmt)

    def insert_task(self, target: TaskTarget, *, priority: int = 100) -> DiscoveryTask:
        """Insert a pending task for ``target``."""
        task = DiscoveryTask(
            catalogue_service_id=target.catalogue_service_id,
            kind=target.kind,
            target_url=target.target_url,
            input_key=target.input_key,
            artifact_id=target.artifact_id,
            status=DiscoveryTaskStatus.PENDING,
            priority=priority,
        )
        self._session.add(task)
        self._session.flush()
        return task

    def reclaim_expired_claims(self, *, now: datetime, max_attempts: int) -> None:
        """Fail expired leases that used ``max_attempts``; return the rest to the pending queue."""
        self._session.execute(fail_exhausted_stmt(now, max_attempts))
        self._session.execute(repend_expired_stmt(now))
        self._session.flush()

    def text_extracted(self, extracted: ExtractedText) -> bool:
        """Return whether a completed ``llm_extract`` of the page under the same input key recorded the same text hash."""
        stmt = select(
            exists().where(
                DiscoveryTask.catalogue_service_id == extracted.catalogue_service_id,
                DiscoveryTask.kind == DiscoveryTaskKind.LLM_EXTRACT,
                DiscoveryTask.target_url == extracted.target_url,
                DiscoveryTask.input_key == extracted.input_key,
                DiscoveryTask.status == DiscoveryTaskStatus.COMPLETED,
                DiscoveryTask.text_hash == extracted.text_hash,
            )
        )
        return bool(self._session.scalar(stmt))

    def requeue_transient(self, *, cutoff: datetime, limit: int) -> int:
        """Return up to ``limit`` transient failures last failed before ``cutoff`` to pending; return how many."""
        return len(self._session.scalars(requeue_transient_stmt(cutoff, limit)).all())

    def list_pending_tasks_for_claim(
        self, *, limit: int, kinds: Sequence[DiscoveryTaskKind], now: datetime
    ) -> list[DiscoveryTask]:
        """Return up to ``limit`` claimable ``kinds`` tasks, by priority then page-completeness-desc (D5, D6).

        The task rows are locked ``FOR UPDATE SKIP LOCKED``, so a claim running on another connection skips them
        instead of receiving them again. The completeness subquery is not locked.
        """
        completeness = page_completeness_subquery()
        stmt = (
            select(DiscoveryTask)
            .outerjoin(completeness, completeness.c.catalogue_service_id == DiscoveryTask.catalogue_service_id)
            .where(*claimable(now), DiscoveryTask.kind.in_(kinds))
        )
        order = _claim_order(completeness.c.page_completeness)
        locked = stmt.order_by(*order).limit(limit).with_for_update(skip_locked=True, of=DiscoveryTask)
        return list(self._session.scalars(locked).all())

    def get_task(self, task_id: UUID) -> DiscoveryTask | None:
        """Return the task with ``task_id``, if any."""
        return self._session.get(DiscoveryTask, task_id)
