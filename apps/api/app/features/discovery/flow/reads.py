"""Reads behind the flow: what each queue has held, the newest run of each run stage and the spend of the last day."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import QueryableAttribute, Session

from app.features.discovery.flow.stage import FlowQueue
from app.models.discovery import DiscoveryRun, DiscoveryRunStatus, DiscoveryTask, DiscoveryTaskKind
from app.models.search import EmbeddingTask
from app.models.snapshot_translation import SnapshotTranslationTask
from app.models.translation import TranslationTask


@dataclass(frozen=True, slots=True)
class Intake:
    """How many tasks a queue has ever held, and how many of them arrived in the last day."""

    total: int
    created_24h: int


NO_INTAKE = Intake(total=0, created_24h=0)


def sum_intakes(intakes: Iterable[Intake]) -> Intake:
    """Return the intake of several queues taken together."""
    collected = list(intakes)
    return Intake(
        total=sum(intake.total for intake in collected),
        created_24h=sum(intake.created_24h for intake in collected),
    )


@dataclass(frozen=True, slots=True)
class LastRun:
    """The newest run of one run stage."""

    status: DiscoveryRunStatus
    stop_reason: str | None
    started_at: datetime
    finished_at: datetime | None


class FlowReads:
    """Count queue intake, find the newest run of each run stage and total the spend of runs since a time."""

    def __init__(self, session: Session) -> None:
        """Bind the reads to ``session``."""
        self._session = session

    def task_intake(self, since: datetime) -> dict[DiscoveryTaskKind, Intake]:
        """Return the intake of every discovery task kind that has ever held a task."""
        recent = func.count().filter(DiscoveryTask.created_at >= since)
        stmt = select(DiscoveryTask.kind, func.count(), recent).group_by(DiscoveryTask.kind)
        return {kind: Intake(int(total), int(created)) for kind, total, created in self._session.execute(stmt).all()}

    def queue_intake(self, since: datetime, *, model: str, locales: Sequence[str]) -> dict[FlowQueue, Intake]:
        """Return the intake of the embedding queue of ``model`` and of the card and page queues of ``locales``."""
        return {
            FlowQueue.EMBEDDING: self._intake(EmbeddingTask.created_at, EmbeddingTask.model == model, since),
            FlowQueue.CARD_TRANSLATION: self._intake(
                TranslationTask.created_at, TranslationTask.locale.in_(locales), since
            ),
            FlowQueue.PAGE_TRANSLATION: self._intake(
                SnapshotTranslationTask.created_at, SnapshotTranslationTask.locale.in_(locales), since
            ),
        }

    def latest_runs(self) -> dict[str, LastRun]:
        """Return the newest run of each run stage, keyed by the stage name the run records."""
        newest = (
            select(DiscoveryRun.stage, func.max(DiscoveryRun.started_at).label("started_at"))
            .where(DiscoveryRun.stage.is_not(None))
            .group_by(DiscoveryRun.stage)
            .subquery()
        )
        stmt = select(DiscoveryRun).join(
            newest, (DiscoveryRun.stage == newest.c.stage) & (DiscoveryRun.started_at == newest.c.started_at)
        )
        return {
            run.stage: LastRun(DiscoveryRunStatus(run.status), run.stop_reason, run.started_at, run.finished_at)
            for run in self._session.scalars(stmt)
            if run.stage is not None
        }

    def spend_since(self, since: datetime) -> list[tuple[str, dict[str, float] | None]]:
        """Return the run stage and recorded spend of every run that started at or after ``since``."""
        stmt = select(DiscoveryRun.stage, DiscoveryRun.spend).where(DiscoveryRun.started_at >= since)
        return [(stage, spend) for stage, spend in self._session.execute(stmt).all() if stage is not None]

    def _intake(self, created_at: QueryableAttribute[datetime], scope: ColumnElement[bool], since: datetime) -> Intake:
        stmt = select(func.count(), func.count().filter(created_at >= since)).where(scope)
        total, created = self._session.execute(stmt).one()
        return Intake(int(total), int(created))
