"""Catalogue queries."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ColumnElement, Select, func, select

from app.features.discovery.repository.base import SessionRepository
from app.models.discovery import CatalogueService, DiscoverySource


def catalogue_list_stmt(*, source: DiscoverySource | None) -> Select:
    """Return the catalogue select, filtered by ``source`` when given."""
    stmt = select(CatalogueService)
    if source is not None:
        stmt = stmt.where(CatalogueService.source == source)
    return stmt


class CatalogueRepository(SessionRepository):
    """Read and add catalogue rows."""

    def get_catalogue_by_source_external_id(
        self, *, source: DiscoverySource, external_id: str
    ) -> CatalogueService | None:
        """Return the catalogue row for ``source`` and ``external_id``, if any."""
        stmt = select(CatalogueService).where(
            CatalogueService.source == source,
            CatalogueService.external_id == external_id,
        )
        return self._session.scalar(stmt)

    def get_catalogue(self, catalogue_id: UUID) -> CatalogueService | None:
        """Return the catalogue row with ``catalogue_id``, if any."""
        return self._session.get(CatalogueService, catalogue_id)

    def add_catalogue(self, row: CatalogueService) -> None:
        """Add ``row`` to the session and flush it."""
        self._session.add(row)
        self._session.flush()

    def count_catalogue(self, *, source: DiscoverySource | None = None) -> int:
        """Count catalogue rows, optionally for one ``source``."""
        stmt = select(func.count()).select_from(catalogue_list_stmt(source=source).subquery())
        return int(self._session.scalar(stmt) or 0)

    def list_catalogue_page(
        self, *, offset: int, limit: int, source: DiscoverySource | None = None
    ) -> list[CatalogueService]:
        """Return one page of catalogue rows, newest first."""
        stmt = catalogue_list_stmt(source=source)
        stmt = stmt.order_by(CatalogueService.updated_at.desc(), CatalogueService.id.desc())
        return list(self._session.scalars(stmt.offset(offset).limit(limit)).all())

    def catalogue_summary(self, *, source: DiscoverySource | None = None) -> tuple[int, dict[str, int], dict[str, int]]:
        """Return the total plus counts grouped by source and by pipeline stage."""
        base = catalogue_list_stmt(source=source).subquery()
        total = int(self._session.scalar(select(func.count()).select_from(base)) or 0)
        return total, self._grouped_counts(base.c.source), self._grouped_counts(base.c.pipeline_stage)

    def _grouped_counts(self, column: ColumnElement[str]) -> dict[str, int]:
        rows = self._session.execute(select(column, func.count()).group_by(column)).all()
        return {str(row[0]): int(row[1]) for row in rows}
