"""Paged task listings for the admin API."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Select, func, select

from app.features.discovery.repository.base import SessionRepository
from app.features.discovery.repository.tasks import QUEUE_ORDER
from app.models.discovery import CatalogueService, DiscoverySource, DiscoveryTask, DiscoveryTaskStatus


@dataclass(frozen=True, slots=True)
class Page:
    """Offset and limit of one result page."""

    offset: int
    limit: int


def _task_list_stmt(*, status: DiscoveryTaskStatus | None, source: DiscoverySource | None) -> Select:
    stmt = select(DiscoveryTask, CatalogueService.source).join(
        CatalogueService, DiscoveryTask.catalogue_service_id == CatalogueService.id
    )
    if status is not None:
        stmt = stmt.where(DiscoveryTask.status == status)
    if source is not None:
        stmt = stmt.where(CatalogueService.source == source)
    return stmt


class TaskListingRepository(SessionRepository):
    """List and count tasks together with their catalogue source."""

    def count_tasks(self, *, status: DiscoveryTaskStatus | None = None, source: DiscoverySource | None = None) -> int:
        """Count tasks, optionally filtered by ``status`` and ``source``."""
        stmt = select(func.count()).select_from(_task_list_stmt(status=status, source=source).subquery())
        return int(self._session.scalar(stmt) or 0)

    def list_tasks_page(
        self,
        page: Page,
        *,
        status: DiscoveryTaskStatus | None = None,
        source: DiscoverySource | None = None,
    ) -> list[tuple[DiscoveryTask, DiscoverySource]]:
        """Return one page of tasks with their catalogue source, in queue order."""
        stmt = _task_list_stmt(status=status, source=source).order_by(*QUEUE_ORDER)
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
