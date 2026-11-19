"""The queue figures of each stage: its ready tasks and what finished in the last day, from the queue summaries the machine API serves."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sqlalchemy.orm import Session

from app.config import settings
from app.features.discovery.artifact_read import ArtifactReadService
from app.features.discovery.flow.stage import FlowQueue, Stage
from app.features.discovery.repository import DiscoveryRepository
from app.features.search.clock import Clock
from app.features.search.queue import EmbeddingQueue
from app.features.translation.queue import TranslationQueue
from app.features.translation.snapshot_queue import SnapshotQueue


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


def _pinned(now: datetime) -> Clock:
    """Return a clock that always reads ``now``, so every queue of one response is measured at the same instant."""
    return lambda: now


class QueueFigureReader:
    """Read the ready and recently finished counts of each stage without leasing or writing anything."""

    def __init__(self, repository: DiscoveryRepository, artifacts: ArtifactReadService) -> None:
        """Bind the reader to ``repository`` for discovery tasks and to ``artifacts`` for the page queue's constructor."""
        self._repo = repository
        self._session: Session = repository.session
        self._artifacts = artifacts
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
        summary = EmbeddingQueue(self._session, _pinned(now)).summary(settings.embedding_model)
        return QueueFigures(summary.pending_ready, summary.completed_24h, summary.failed_24h)

    def _card_figures(self, now: datetime) -> QueueFigures:
        return _sum_locales(TranslationQueue(self._session, _pinned(now)).summary().locales)

    def _page_figures(self, now: datetime) -> QueueFigures:
        return _sum_locales(SnapshotQueue(self._session, self._artifacts, _pinned(now)).summary().locales)
