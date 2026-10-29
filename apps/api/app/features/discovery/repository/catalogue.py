"""Catalogue queries."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ColumnElement, Select, func, select

from app.features.discovery.repository.base import SessionRepository
from app.features.discovery.repository.catalogue_filter import CatalogueFilter
from app.models.discovery import CatalogueService, DiscoverySource


def catalogue_list_stmt(catalogue_filter: CatalogueFilter) -> Select:
    """Return the catalogue select narrowed by ``catalogue_filter``."""
    return select(CatalogueService).where(*catalogue_filter.conditions())


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

    def count_catalogue(self, catalogue_filter: CatalogueFilter | None = None) -> int:
        """Count the catalogue rows that match ``catalogue_filter``."""
        stmt = select(func.count()).select_from(catalogue_list_stmt(catalogue_filter or CatalogueFilter()).subquery())
        return int(self._session.scalar(stmt) or 0)

    def list_catalogue_page(
        self, *, offset: int, limit: int, catalogue_filter: CatalogueFilter | None = None
    ) -> list[CatalogueService]:
        """Return one page of the rows that match ``catalogue_filter``, in its order."""
        catalogue_filter = catalogue_filter or CatalogueFilter()
        stmt = catalogue_list_stmt(catalogue_filter).order_by(*catalogue_filter.ordering())
        return list(self._session.scalars(stmt.offset(offset).limit(limit)).all())

    def catalogue_summary(
        self, catalogue_filter: CatalogueFilter | None = None
    ) -> tuple[int, dict[str, int], dict[str, int]]:
        """Return the total plus counts grouped by source and by pipeline stage of the matching rows."""
        base = catalogue_list_stmt(catalogue_filter or CatalogueFilter()).subquery()
        total = int(self._session.scalar(select(func.count()).select_from(base)) or 0)
        return total, self._grouped_counts(base.c.source), self._grouped_counts(base.c.pipeline_stage)

    def _grouped_counts(self, column: ColumnElement[str]) -> dict[str, int]:
        rows = self._session.execute(select(column, func.count()).group_by(column)).all()
        return {str(row[0]): int(row[1]) for row in rows}
