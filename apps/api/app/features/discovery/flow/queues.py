"""The queue figures of each stage: its ready tasks and what finished in the last day, from the existing queue summaries."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.config import settings
from app.features.discovery.flow.stage import FlowQueue, Stage
from app.features.discovery.repository import DiscoveryRepository
from app.features.search.embedding_repository import EmbeddingRepository
from app.features.translation.repository import TranslationRepository
from app.features.translation.snapshot_repository import SnapshotRepository


@dataclass(frozen=True, slots=True)
class QueueFigures:
    """The ready tasks of a stage, and the tasks it finished or failed in the last day."""

    ready: int
    completed_24h: int
    failed_24h: int


class _LocaleCounts(Protocol):
    """The ready and 24 h counts of one locale in a translation or snapshot queue summary."""

    @property
    def pending_ready(self) -> int:
        """Return the ready tasks of the locale."""
        ...

    @property
    def completed_24h(self) -> int:
        """Return the tasks of the locale completed in the last day."""
        ...

    @property
    def failed_24h(self) -> int:
        """Return the tasks of the locale failed in the last day."""
        ...


def _sum_locales(rows: Sequence[_LocaleCounts]) -> QueueFigures:
    return QueueFigures(
        ready=sum(row.pending_ready for row in rows),
        completed_24h=sum(row.completed_24h for row in rows),
        failed_24h=sum(row.failed_24h for row in rows),
    )


class QueueFigureReader:
    """Read the ready and recently finished counts of each stage without leasing or writing anything."""

    def __init__(self, repository: DiscoveryRepository) -> None:
        """Bind the reader to ``repository`` and to the queue repositories of its session."""
        self._repo = repository
        session = repository.session
        self._embedding = EmbeddingRepository(session)
        self._translation = TranslationRepository(session)
        self._snapshots = SnapshotRepository(session)
        self._by_queue: dict[FlowQueue, Callable[[datetime], QueueFigures]] = {
            FlowQueue.EMBEDDING: self._embedding_figures,
            FlowQueue.CARD_TRANSLATION: self._card_figures,
            FlowQueue.PAGE_TRANSLATION: self._page_figures,
        }

    def figures(self, stage: Stage, now: datetime) -> QueueFigures:
        """Return the figures of ``stage`` at ``now``: a discovery task stage reads its kinds, a table stage its queue."""
        if stage.queue is None:
            return self._task_figures(stage, now)
        return self._by_queue[stage.queue](now)

    def _task_figures(self, stage: Stage, now: datetime) -> QueueFigures:
        summary = self._repo.task_summary(kinds=stage.task_kinds, now=now)
        return QueueFigures(summary.pending_ready, summary.completed_24h, summary.failed_24h)

    def _embedding_figures(self, now: datetime) -> QueueFigures:
        summary = self._embedding.summary(settings.embedding_model, now)
        return QueueFigures(summary.pending_ready, summary.completed_24h, summary.failed_24h)

    def _card_figures(self, now: datetime) -> QueueFigures:
        return _sum_locales(self._translation.summary(settings.translation_target_locale_codes, now))

    def _page_figures(self, now: datetime) -> QueueFigures:
        return _sum_locales(self._snapshots.summary(settings.translation_target_locale_codes, now))
