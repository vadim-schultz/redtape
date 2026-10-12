"""Persistence for discovery admin reads."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.discovery import CatalogueService, DiscoverySource, DiscoveryTask, DiscoveryTaskStatus


def _task_list_stmt(
    *,
    status: DiscoveryTaskStatus | None,
    source: DiscoverySource | None,
) -> Select:
    stmt = select(DiscoveryTask, CatalogueService.source).join(
        CatalogueService, DiscoveryTask.catalogue_service_id == CatalogueService.id
    )
    if status is not None:
        stmt = stmt.where(DiscoveryTask.status == status)
    if source is not None:
        stmt = stmt.where(CatalogueService.source == source)
    return stmt


def _catalogue_list_stmt(*, source: DiscoverySource | None) -> Select:
    stmt = select(CatalogueService)
    if source is not None:
        stmt = stmt.where(CatalogueService.source == source)
    return stmt


class DiscoveryRepository:
    """Read-only queries for discovery admin screens."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def count_tasks(
        self,
        *,
        status: DiscoveryTaskStatus | None = None,
        source: DiscoverySource | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(_task_list_stmt(status=status, source=source).subquery())
        return int(self._session.scalar(stmt) or 0)

    def list_tasks_page(
        self,
        *,
        offset: int,
        limit: int,
        status: DiscoveryTaskStatus | None = None,
        source: DiscoverySource | None = None,
    ) -> list[tuple[DiscoveryTask, DiscoverySource]]:
        stmt = _task_list_stmt(status=status, source=source)
        stmt = stmt.order_by(DiscoveryTask.priority.asc(), DiscoveryTask.created_at.asc(), DiscoveryTask.id.asc())
        stmt = stmt.offset(offset).limit(limit)
        return list(self._session.execute(stmt).tuples().all())

    def count_catalogue(self, *, source: DiscoverySource | None = None) -> int:
        stmt = select(func.count()).select_from(_catalogue_list_stmt(source=source).subquery())
        return int(self._session.scalar(stmt) or 0)

    def list_catalogue_page(
        self,
        *,
        offset: int,
        limit: int,
        source: DiscoverySource | None = None,
    ) -> list[CatalogueService]:
        stmt = _catalogue_list_stmt(source=source)
        stmt = stmt.order_by(CatalogueService.updated_at.desc(), CatalogueService.id.desc())
        stmt = stmt.offset(offset).limit(limit)
        return list(self._session.scalars(stmt).all())

    def catalogue_summary(self, *, source: DiscoverySource | None = None) -> tuple[int, dict[str, int], dict[str, int]]:
        base = _catalogue_list_stmt(source=source).subquery()
        total = int(self._session.scalar(select(func.count()).select_from(base)) or 0)
        by_source_rows = self._session.execute(select(base.c.source, func.count()).group_by(base.c.source)).all()
        by_stage_rows = self._session.execute(
            select(base.c.pipeline_stage, func.count()).group_by(base.c.pipeline_stage)
        ).all()
        by_source = {str(row[0]): int(row[1]) for row in by_source_rows}
        by_stage = {str(row[0]): int(row[1]) for row in by_stage_rows}
        return total, by_source, by_stage

    def get_catalogue(self, catalogue_id: UUID) -> CatalogueService | None:
        return self._session.get(CatalogueService, catalogue_id)
