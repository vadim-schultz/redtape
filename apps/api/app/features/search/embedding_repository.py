"""Reads and writes behind the embedding queue: the text a task serves, the stored vectors and the counts."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.features.discovery.repository.base import SessionRepository
from app.features.search.leased_queue import ready_clause
from app.features.search.text import BuiltText
from app.models.search import CandidateEmbedding, EmbeddingTask, WorkTaskStatus
from app.models.search import CandidateSearchText as SearchText
from app.schema.search.machine import EmbeddingSummaryResponse
from app.shared.queue_stats import age_seconds, finished_recently, oldest_ready

TextKey = tuple[UUID, str]
"""``(candidate_id, locale)``: the key of a search text."""


class EmbeddingRepository(SessionRepository):
    """Read the search text of tasks, write vectors and count the queue."""

    def texts_for(self, tasks: Sequence[EmbeddingTask]) -> dict[TextKey, BuiltText]:
        """Return the current search text of every task's ``(candidate, locale)`` that still has one."""
        keys = [(task.candidate_id, task.locale) for task in tasks]
        if not keys:
            return {}
        stmt = select(SearchText.candidate_id, SearchText.locale, SearchText.text, SearchText.content_hash).where(
            tuple_(SearchText.candidate_id, SearchText.locale).in_(keys)
        )
        return {
            (row.candidate_id, row.locale): BuiltText(row.locale, row.text, row.content_hash)
            for row in self._session.execute(stmt)
        }

    def locked_text(self, candidate_id: UUID, locale: str) -> BuiltText | None:
        """Return the current search text and hold a share lock on it until the transaction ends.

        The lock keeps a rewrite of the text from slipping in between a hash check and the vector it guards: the
        rewrite waits, then finds the task settled and queues its own.
        """
        stmt = (
            select(SearchText.locale, SearchText.text, SearchText.content_hash)
            .where(SearchText.candidate_id == candidate_id, SearchText.locale == locale)
            .with_for_update(read=True)
        )
        row = self._session.execute(stmt).first()
        return BuiltText(row.locale, row.text, row.content_hash) if row else None

    def store_embedding(self, task: EmbeddingTask, vector: Sequence[float]) -> None:
        """Insert or replace the vector of the task's ``(candidate, model, locale)`` at the task's text hash."""
        values = {"dim": len(vector), "text_hash": task.text_hash, "embedding": list(vector)}
        insert = pg_insert(CandidateEmbedding).values(
            candidate_id=task.candidate_id, model=task.model, locale=task.locale, **values
        )
        self._session.execute(
            insert.on_conflict_do_update(
                index_elements=[CandidateEmbedding.candidate_id, CandidateEmbedding.model, CandidateEmbedding.locale],
                set_={**values, "created_at": func.now()},
            )
        )

    def summary(self, model: str, now: datetime) -> EmbeddingSummaryResponse:
        """Count the ready, claimed and failed tasks of ``model`` and the search texts without a current vector."""
        ready = ready_clause(EmbeddingTask, now)
        tasks = select(
            func.count().filter(*ready),
            func.count().filter(EmbeddingTask.status == WorkTaskStatus.CLAIMED),
            func.count().filter(EmbeddingTask.status == WorkTaskStatus.FAILED),
            oldest_ready(EmbeddingTask.created_at, ready),
            finished_recently(EmbeddingTask.status == WorkTaskStatus.COMPLETED, EmbeddingTask.updated_at, now),
            finished_recently(EmbeddingTask.status == WorkTaskStatus.FAILED, EmbeddingTask.updated_at, now),
        ).where(EmbeddingTask.model == model)
        ready_count, claimed, failed, oldest, completed, failed_recent = self._session.execute(tasks).one()
        return EmbeddingSummaryResponse(
            pending_ready=ready_count,
            claimed=claimed,
            failed=failed,
            stale_candidates=self._stale_texts(model),
            oldest_pending_age_seconds=age_seconds(oldest, now),
            completed_24h=completed,
            failed_24h=failed_recent,
        )

    def _stale_texts(self, model: str) -> int:
        """Return how many search texts have no embedding of ``model`` at their current hash."""
        embedding = CandidateEmbedding
        stmt = (
            select(func.count())
            .select_from(SearchText)
            .outerjoin(
                embedding,
                (embedding.candidate_id == SearchText.candidate_id)
                & (embedding.locale == SearchText.locale)
                & (embedding.model == model),
            )
            .where(embedding.text_hash.is_(None) | (embedding.text_hash != SearchText.content_hash))
        )
        return int(self._session.scalar(stmt) or 0)
