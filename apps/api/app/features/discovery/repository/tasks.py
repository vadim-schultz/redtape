"""Discovery task queue queries."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, exists, func, select
from sqlalchemy.orm import Session

from app.features.discovery.repository.base import SessionRepository
from app.features.discovery.repository.task_clauses import (
    claimable,
    fail_exhausted_stmt,
    repend_expired_stmt,
    requeue_superseded_stmt,
    requeue_transient_stmt,
    superseded_ids_stmt,
)
from app.features.discovery.repository.task_page_completeness import page_completeness_subquery
from app.features.discovery.repository.task_target import ExtractedText, TaskTarget, identity_clauses
from app.models.discovery import (
    DiscoveryTask,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)
from app.models.fair_selection_state import FairSelectionState

# Admin/general task listing order (task_sort.py): priority, then created_at, then id. Unaffected by
# page completeness — that heuristic is claim-order-only, see ``_claim_order`` below.
QUEUE_ORDER = (DiscoveryTask.priority.asc(), DiscoveryTask.created_at.asc(), DiscoveryTask.id.asc())


def get_phase_for_discovery_page(session: Session, catalogue_service_id: UUID) -> int:
    """Read phase for a discovery page; default to phase 1 if not found.

    Discovery entity_id is catalogue_service_id (page).
    """
    state = session.query(FairSelectionState).filter(
        FairSelectionState.pipeline == "discovery",
        FairSelectionState.entity_id == catalogue_service_id
    ).first()
    return state.phase if state else 1


def _claim_order(page_completeness: ColumnElement) -> tuple[ColumnElement, ...]:
    """Return the claim order: phase, priority, page-completeness-desc, created_at, id.

    Phase (ASC) ensures breadth-first (phase 1) items claim before depth-first (phase 2).
    Within phase and priority, page-completeness-desc tie-breaks to claim pages nearing
    completion before emptier pages (original D7 logic, now under phase constraint).
    """
    return (
        DiscoveryTask.phase.asc(),
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

    def insert_task(self, target: TaskTarget, *, priority: int = 100, phase: int = 1) -> DiscoveryTask:
        """Insert a pending task for ``target`` with optional phase override."""
        task = DiscoveryTask(
            catalogue_service_id=target.catalogue_service_id,
            kind=target.kind,
            target_url=target.target_url,
            input_key=target.input_key,
            artifact_id=target.artifact_id,
            status=DiscoveryTaskStatus.PENDING,
            priority=priority,
            phase=phase,
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

    def last_render_completed_at(self, catalogue_id: UUID, target_url: str) -> datetime | None:
        """Return when the newest completed render of the page finished, or ``None`` when no render of it has completed."""
        stmt = select(func.max(DiscoveryTask.updated_at)).where(
            DiscoveryTask.catalogue_service_id == catalogue_id,
            DiscoveryTask.kind == DiscoveryTaskKind.RENDER_PAGE,
            DiscoveryTask.target_url == target_url,
            DiscoveryTask.status == DiscoveryTaskStatus.COMPLETED,
        )
        return self._session.scalar(stmt)

    def requeue_transient(self, *, cutoff: datetime, limit: int) -> int:
        """Return up to ``limit`` transient failures last failed before ``cutoff`` to pending; return how many."""
        return len(self._session.scalars(requeue_transient_stmt(cutoff, limit)).all())

    def superseded_task_ids(self, *, kind: DiscoveryTaskKind, input_key: str, limit: int) -> list[UUID]:
        """Return the ids of up to ``limit`` superseded tasks of ``kind`` under ``input_key``, changing nothing."""
        return list(self._session.scalars(superseded_ids_stmt(kind, input_key, limit)).all())

    def requeue_superseded(self, *, kind: DiscoveryTaskKind, input_key: str, limit: int) -> list[UUID]:
        """Re-pend up to ``limit`` superseded tasks of ``kind`` under ``input_key``; return the ids that were re-pended.

        The selected rows are taken ``FOR UPDATE SKIP LOCKED``, so a concurrent requeue skips them.
        """
        locked = superseded_ids_stmt(kind, input_key, limit).with_for_update(skip_locked=True, of=DiscoveryTask)
        stmt = requeue_superseded_stmt(locked, input_key)
        return list(self._session.scalars(stmt).all())

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
