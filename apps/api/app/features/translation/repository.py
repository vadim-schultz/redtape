"""Reads and writes of the translation index and its summary counts."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import NamedTuple
from uuid import UUID

from sqlalchemy import func, select

from app.features.discovery.repository.base import SessionRepository
from app.features.search.leased_queue import ready_clause
from app.features.translation.store import StoredObject, TranslationPayload
from app.models.discovery import DiscoveryDocumentCandidate as Candidate
from app.models.search import WorkTaskStatus
from app.models.translation import CandidateTranslation, TranslationSource, TranslationTask
from app.schema.translation.machine import TranslationLocaleSummary


class IndexState(NamedTuple):
    """What the enqueue decision needs from an index row."""

    source_hash: str
    source: TranslationSource


class QueueCounts(NamedTuple):
    """The tasks of one locale that are ready, claimed and failed."""

    pending_ready: int = 0
    claimed: int = 0
    failed: int = 0


class TranslationRepository(SessionRepository):
    """Read the index rows of translations, write them and count them."""

    def index_states(self, candidate_ids: Sequence[UUID], locales: Sequence[str]) -> dict[tuple[UUID, str], IndexState]:
        """Return the hash and provenance of every stored translation of ``candidate_ids`` in ``locales``."""
        row = CandidateTranslation
        stmt = select(row.candidate_id, row.locale, row.source_hash, row.source).where(
            row.candidate_id.in_(candidate_ids), row.locale.in_(locales)
        )
        return {(r.candidate_id, r.locale): IndexState(r.source_hash, r.source) for r in self._session.execute(stmt)}

    def share_lock_candidate_of(self, task_id: UUID) -> None:
        """Hold a share lock on the candidate of ``task_id`` until the transaction ends.

        A rewrite of the German title waits for it, so no change slips in between the hash check and the stored text.
        Callers take it before the task lock, the order every candidate writer uses (candidate, then task).
        """
        self._session.flush()
        owner = select(TranslationTask.candidate_id).where(TranslationTask.id == task_id).scalar_subquery()
        self._session.execute(select(Candidate.id).where(Candidate.id == owner).with_for_update(read=True))

    def locked_row(self, candidate_id: UUID, locale: str) -> CandidateTranslation | None:
        """Return the index row of ``(candidate, locale)`` and lock it, or ``None`` when there is none."""
        stmt = (
            select(CandidateTranslation)
            .where(CandidateTranslation.candidate_id == candidate_id, CandidateTranslation.locale == locale)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return self._session.scalars(stmt).first()

    def upsert_row(
        self,
        candidate_id: UUID,
        payload: TranslationPayload,
        stored: StoredObject,
        existing: CandidateTranslation | None,
    ) -> None:
        """Point the machine-translation index row of ``(candidate, locale)`` at ``stored``, creating it when absent."""
        row = existing or CandidateTranslation(candidate_id=candidate_id, locale=payload.locale)
        row.source_hash, row.source = payload.source_hash, TranslationSource.MT
        row.engine, row.model = payload.engine, payload.model
        row.storage_key, row.content_sha256, row.size_bytes = stored.key, stored.content_sha256, stored.size_bytes
        self._session.add(row)
        self._session.flush()

    def summary(self, locales: Sequence[str], now: datetime) -> list[TranslationLocaleSummary]:
        """Count the queue and the store of every locale in ``locales``, in that order."""
        queue, translated, stale = self._queue_counts(now), self._translated_counts(), self._stale_counts()
        return [
            TranslationLocaleSummary(
                locale=locale,
                stale=stale.get(locale, 0),
                translated=translated.get(locale, 0),
                **queue.get(locale, QueueCounts())._asdict(),
            )
            for locale in locales
        ]

    def _queue_counts(self, now: datetime) -> dict[str, QueueCounts]:
        task = TranslationTask
        stmt = select(
            task.locale,
            func.count().filter(*ready_clause(task, now)),
            func.count().filter(task.status == WorkTaskStatus.CLAIMED),
            func.count().filter(task.status == WorkTaskStatus.FAILED),
        ).group_by(task.locale)
        return {
            locale: QueueCounts(ready, claimed, failed)
            for locale, ready, claimed, failed in self._session.execute(stmt)
        }

    def _translated_counts(self) -> dict[str, int]:
        stmt = select(CandidateTranslation.locale, func.count()).group_by(CandidateTranslation.locale)
        return dict(self._session.execute(stmt).tuples().all())

    def _stale_counts(self) -> dict[str, int]:
        """Count stored translations that an open task is replacing with a newer German unit, by locale."""
        row, task = CandidateTranslation, TranslationTask
        replacing = (
            (task.candidate_id == row.candidate_id)
            & (task.locale == row.locale)
            & task.status.in_((WorkTaskStatus.PENDING, WorkTaskStatus.CLAIMED))
            & (task.source_hash != row.source_hash)
        )
        stmt = select(row.locale, func.count()).join(task, replacing).group_by(row.locale)
        return dict(self._session.execute(stmt).tuples().all())
