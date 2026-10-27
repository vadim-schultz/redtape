"""Paged task listings for the admin API."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import ColumnElement, Select, func, select

from app.features.discovery.repository.base import SessionRepository
from app.features.discovery.repository.tasks import QUEUE_ORDER
from app.models.discovery import (
    CatalogueService,
    DiscoverySource,
    DiscoveryTask,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)


@dataclass(frozen=True, slots=True)
class Page:
    """Offset and limit of one result page."""

    offset: int
    limit: int


@dataclass(frozen=True, slots=True)
class TaskFilter:
    """Optional status, source and kind a task listing is narrowed to."""

    status: DiscoveryTaskStatus | None = None
    source: DiscoverySource | None = None
    kind: DiscoveryTaskKind | None = None

    def conditions(self) -> list[ColumnElement[bool]]:
        """Return the where-clauses of the filters that are set."""
        pairs = (
            (DiscoveryTask.status, self.status),
            (CatalogueService.source, self.source),
            (DiscoveryTask.kind, self.kind),
        )
        return [column == value for column, value in pairs if value is not None]


def _task_list_stmt(task_filter: TaskFilter) -> Select:
    stmt = select(DiscoveryTask, CatalogueService.source).join(
        CatalogueService, DiscoveryTask.catalogue_service_id == CatalogueService.id
    )
    return stmt.where(*task_filter.conditions())


class TaskListingRepository(SessionRepository):
    """List and count tasks together with their catalogue source."""

    def count_tasks(self, task_filter: TaskFilter | None = None) -> int:
        """Count tasks matching ``task_filter``."""
        stmt = select(func.count()).select_from(_task_list_stmt(task_filter or TaskFilter()).subquery())
        return int(self._session.scalar(stmt) or 0)

    def list_tasks_page(
        self, page: Page, task_filter: TaskFilter | None = None
    ) -> list[tuple[DiscoveryTask, DiscoverySource]]:
        """Return one page of tasks matching ``task_filter`` with their catalogue source, in queue order."""
        stmt = _task_list_stmt(task_filter or TaskFilter()).order_by(*QUEUE_ORDER)
        return list(self._session.execute(stmt.offset(page.offset).limit(page.limit)).tuples().all())

    def list_catalogue_tasks(self, catalogue_id: UUID) -> list[tuple[DiscoveryTask, DiscoverySource]]:
        """Return every task of one catalogue row, oldest first."""
        stmt = (
            select(DiscoveryTask, CatalogueService.source)
            .join(CatalogueService, DiscoveryTask.catalogue_service_id == CatalogueService.id)
            .where(DiscoveryTask.catalogue_service_id == catalogue_id)
            .order_by(DiscoveryTask.created_at.asc(), DiscoveryTask.id.asc())
        )
        return list(self._session.execute(stmt).tuples().all())
