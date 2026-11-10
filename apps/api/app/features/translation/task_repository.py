"""Writes to ``translation_task`` that enqueueing needs: the idempotent upsert of a pending task and its retirement."""

from __future__ import annotations

from collections.abc import Collection
from uuid import UUID

from sqlalchemy import and_, delete, func, or_, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.features.discovery.repository.base import SessionRepository
from app.features.search.task_states import OPEN_TASK_PREDICATE
from app.models.search import WorkTaskStatus
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
