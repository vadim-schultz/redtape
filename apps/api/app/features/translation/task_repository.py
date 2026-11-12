"""Writes to the translation task tables that enqueueing needs: idempotent upserts of pending tasks and retirement."""

from __future__ import annotations

from collections.abc import Collection
from uuid import UUID

from sqlalchemy import and_, delete, func, or_, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.features.discovery.repository.base import SessionRepository
from app.features.search.task_states import OPEN_TASK_PREDICATE
from app.models.search import WorkTaskStatus
from app.models.snapshot_translation import SnapshotTranslationTask
from app.models.translation import TranslationTask


class TaskRepository(SessionRepository):
    """Queue and unqueue translation tasks."""

    def upsert_pending(self, candidate_id: UUID, locale: str, source_hash: str, priority: int) -> bool:
        """Queue the unit, or move an open pending task to ``source_hash`` and ``priority``; ``True`` when a row changed.

        A claimed task and a pending task that is already up to date are left untouched, so a repeat changes nothing.
        """
        insert = pg_insert(TranslationTask).values(
            candidate_id=candidate_id, locale=locale, source_hash=source_hash, priority=priority
        )
        upsert = insert.on_conflict_do_update(
            index_elements=[TranslationTask.candidate_id, TranslationTask.locale],
            index_where=OPEN_TASK_PREDICATE,
            set_={
                "source_hash": insert.excluded.source_hash,
                "priority": insert.excluded.priority,
                "updated_at": func.now(),
            },
            where=and_(
                TranslationTask.status == WorkTaskStatus.PENDING,
                or_(TranslationTask.source_hash != source_hash, TranslationTask.priority != priority),
            ),
        )
        return self._session.execute(upsert.returning(TranslationTask.id)).first() is not None

    def upsert_snapshot_pending(self, key: tuple[UUID, str], source_hash: str, priority: int) -> bool:
        """Queue the snapshot of ``key`` (catalogue row, locale), or move its open pending task; ``True`` if a row changed.

        A claimed task is left alone. A completed task is not an open one, so the upsert never touches it: new work is
        a separate pending row, and whether new work is needed at all is decided by the caller.
        """
        catalogue_service_id, locale = key
        insert = pg_insert(SnapshotTranslationTask).values(
            catalogue_service_id=catalogue_service_id, locale=locale, source_hash=source_hash, priority=priority
        )
        upsert = insert.on_conflict_do_update(
            index_elements=[SnapshotTranslationTask.catalogue_service_id, SnapshotTranslationTask.locale],
            index_where=OPEN_TASK_PREDICATE,
            set_={
                "source_hash": insert.excluded.source_hash,
                "priority": insert.excluded.priority,
                "updated_at": func.now(),
            },
            where=and_(
                SnapshotTranslationTask.status == WorkTaskStatus.PENDING,
                or_(
                    SnapshotTranslationTask.source_hash != source_hash,
                    SnapshotTranslationTask.priority != priority,
                ),
            ),
        )
        return self._session.execute(upsert.returning(SnapshotTranslationTask.id)).first() is not None

    def retire_pending(self, slots: Collection[tuple[UUID, str]]) -> None:
        """Delete the pending tasks of ``(candidate, locale)`` pairs whose translation no longer needs work."""
        if not slots:
            return
        self._session.execute(
            delete(TranslationTask).where(
                tuple_(TranslationTask.candidate_id, TranslationTask.locale).in_(list(slots)),
                TranslationTask.status == WorkTaskStatus.PENDING,
            )
        )
