"""Reads and writes of the snapshot translation index rows, and the per-locale counts of the snapshot queue and store."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Final
from uuid import UUID

from sqlalchemy import ColumnElement, func, select

from app.features.discovery.repository.base import SessionRepository
from app.features.search.leased_queue import ready_clause
from app.features.translation.repository import QueueCounts
from app.models.search import WorkTaskStatus
from app.models.snapshot_translation import SnapshotTranslation, SnapshotTranslationTask
from app.schema.translation.snapshot_machine import SnapshotLocaleSummary

PageKey = tuple[UUID, str]
"""``(catalogue row id, locale)``: the key of one page translation and of its open task."""
SKIPPED_ENGINE: Final = "none"
"""The engine column of a skip marker: no engine ran, because the page was not translated."""


def page_key(task: SnapshotTranslationTask) -> PageKey:
    """Return the key of the page translation that ``task`` is for."""
    return task.catalogue_service_id, task.locale


@dataclass(frozen=True, slots=True)
class SnapshotRowValues:
    """Every column of one index row that a settle step writes; ``None`` clears a column."""

    artifact_sha256: str
    source_hash: str
    engine: str
    model: str | None
    storage_key: str | None
    content_sha256: str | None
    size_bytes: int | None
    truncated: bool
    skipped_reason: str | None

    @classmethod
    def skip_marker(cls, artifact_sha256: str, source_hash: str, reason: str) -> SnapshotRowValues:
        """Return the values of a marker that records a page skipped for ``reason``; a marker has no object."""
        return cls(artifact_sha256, source_hash, SKIPPED_ENGINE, None, None, None, None, False, reason)


class SnapshotRepository(SessionRepository):
    """Read and write the snapshot index rows and count the snapshot queue and store."""

    def stored_hash(self, key: PageKey) -> str | None:
        """Return the hash of the text stored for ``key``, or ``None`` when the page was never translated."""
        row = self._session.get(SnapshotTranslation, key)
        return None if row is None else row.source_hash

    def locked_row(self, key: PageKey) -> SnapshotTranslation | None:
        """Return the index row of ``key`` and lock it until the transaction ends, or ``None`` when there is none."""
        return self._session.get(SnapshotTranslation, key, with_for_update=True, populate_existing=True)

    def upsert_row(self, key: PageKey, values: SnapshotRowValues) -> None:
        """Point the index row of ``key`` at ``values``, creating the row when there is none."""
        row = self._session.get(SnapshotTranslation, key)
        if row is None:
            row = SnapshotTranslation(catalogue_service_id=key[0], locale=key[1])
        row.artifact_sha256, row.source_hash = values.artifact_sha256, values.source_hash
        row.engine, row.model = values.engine, values.model
        row.storage_key, row.content_sha256, row.size_bytes = (
            values.storage_key,
            values.content_sha256,
            values.size_bytes,
        )
        row.truncated, row.skipped_reason = values.truncated, values.skipped_reason
        self._session.add(row)
        self._session.flush()

    def refresh_artifact(self, key: PageKey, artifact_sha256: str) -> None:
        """Record that the stored text of ``key`` still matches the artifact ``artifact_sha256``."""
        row = self._session.get(SnapshotTranslation, key)
        assert row is not None
        row.artifact_sha256 = artifact_sha256
        self._session.flush()

    def summary(self, locales: Sequence[str], now: datetime) -> list[SnapshotLocaleSummary]:
        """Count the queue, the stored pages, the skip markers and the stale pages of every locale in ``locales``."""
        queue = self._queue_counts(now)
        translated = self._index_counts(SnapshotTranslation.storage_key.is_not(None))
        skipped = self._index_counts(SnapshotTranslation.skipped_reason.is_not(None))
        stale = self._stale_counts()
        return [
            SnapshotLocaleSummary(
                locale=locale,
                translated=translated.get(locale, 0),
                stale=stale.get(locale, 0),
                skipped=skipped.get(locale, 0),
                **queue.get(locale, QueueCounts())._asdict(),
            )
            for locale in locales
        ]

    def _queue_counts(self, now: datetime) -> dict[str, QueueCounts]:
        task = SnapshotTranslationTask
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

    def _index_counts(self, condition: ColumnElement[bool]) -> dict[str, int]:
        row = SnapshotTranslation
        stmt = select(row.locale, func.count()).where(condition).group_by(row.locale)
        return dict(self._session.execute(stmt).tuples().all())

    def _stale_counts(self) -> dict[str, int]:
        """Count stored pages that an open task replaces with an artifact other than the one they were made from."""
        row, task = SnapshotTranslation, SnapshotTranslationTask
        replacing = (
            (task.catalogue_service_id == row.catalogue_service_id)
            & (task.locale == row.locale)
            & task.status.in_((WorkTaskStatus.PENDING, WorkTaskStatus.CLAIMED))
            & (task.source_hash != row.artifact_sha256)
        )
        stmt = (
            select(row.locale, func.count())
            .join(task, replacing)
            .where(row.storage_key.is_not(None))
            .group_by(row.locale)
        )
        return dict(self._session.execute(stmt).tuples().all())
