"""Hash-aware, idempotent enqueue of embedding tasks."""

from __future__ import annotations

import enum
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.features.discovery.repository.base import SessionRepository
from app.features.search.task_states import OPEN_TASK_PREDICATE
from app.features.search.text import BuiltText
from app.models.search import CandidateEmbedding, EmbeddingTask, WorkTaskStatus


class EnqueueOutcome(enum.StrEnum):
    """What a text change did to the queue."""

    QUEUED = "queued"
    LEFT_OPEN = "left_open"
    CURRENT = "current"


class EmbeddingEnqueuer(SessionRepository):
    """Queue one embedding task per ``(candidate, model, locale)`` whose text is not yet embedded."""

    def __init__(self, session: Session, model: str) -> None:
        """Bind the enqueuer to ``session`` and the embedding ``model`` the tasks are for."""
        super().__init__(session)
        self._model = model

    def enqueue(self, candidate_id: UUID, built: BuiltText) -> EnqueueOutcome:
        """Queue ``built`` for embedding unless the stored embedding already has its hash.

        An open pending task takes the new hash; an open claimed task is left alone, because its result will be
        rejected as stale and the task re-queued when it is settled.
        """
        if self._embedded_hash(candidate_id, built.locale) == built.content_hash:
            self._retire_pending(candidate_id, built.locale)
            return EnqueueOutcome.CURRENT
        queued = self._upsert_pending(candidate_id, built)
        return EnqueueOutcome.QUEUED if queued else EnqueueOutcome.LEFT_OPEN

    def _embedded_hash(self, candidate_id: UUID, locale: str) -> str | None:
        stmt = select(CandidateEmbedding.text_hash).where(
            CandidateEmbedding.candidate_id == candidate_id,
            CandidateEmbedding.model == self._model,
            CandidateEmbedding.locale == locale,
        )
        return self._session.scalar(stmt)

    def _retire_pending(self, candidate_id: UUID, locale: str) -> None:
        self._session.execute(
            delete(EmbeddingTask).where(
                EmbeddingTask.candidate_id == candidate_id,
                EmbeddingTask.model == self._model,
                EmbeddingTask.locale == locale,
                EmbeddingTask.status == WorkTaskStatus.PENDING,
            )
        )

    def _upsert_pending(self, candidate_id: UUID, built: BuiltText) -> bool:
        insert = pg_insert(EmbeddingTask).values(
            candidate_id=candidate_id, model=self._model, locale=built.locale, text_hash=built.content_hash
        )
        upsert = insert.on_conflict_do_update(
            index_elements=[EmbeddingTask.candidate_id, EmbeddingTask.model, EmbeddingTask.locale],
            index_where=OPEN_TASK_PREDICATE,
            set_={"text_hash": insert.excluded.text_hash, "updated_at": func.now()},
            where=(EmbeddingTask.status == WorkTaskStatus.PENDING) & (EmbeddingTask.text_hash != built.content_hash),
        )
        return self._session.execute(upsert.returning(EmbeddingTask.id)).first() is not None
