"""Stale portal pages: the pages whose newest fetch is old enough to refresh, and that have no fetch still open."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, Subquery, exists, func, select

from app.features.discovery.repository.base import SessionRepository
from app.models.discovery import (
    CatalogueService,
    DiscoveryFetchLog,
    DiscoveryTask,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)

OPEN_FETCH_STATUSES = (DiscoveryTaskStatus.PENDING, DiscoveryTaskStatus.CLAIMED)
"""A fetch in one of these states has not run yet, so its page is not due another refresh."""


@dataclass(frozen=True, slots=True)
class StaleFetchRow:
    """A portal page and the time its newest fetch finished."""

    catalogue_service_id: UUID
    target_url: str
    last_fetched_at: datetime


class StaleFetchRepository(SessionRepository):
    """Find the portal pages whose newest fetch finished at or before a cutoff."""

    def stale_fetch_targets(self, *, cutoff: datetime, limit: int) -> list[StaleFetchRow]:
        """Return up to ``limit`` pages whose newest fetch finished at or before ``cutoff``, stalest first.

        A page is a catalogue row's current portal URL. A page with no logged fetch is not listed, and neither is one
        with a fetch of it still pending or claimed.
        """
        latest = _latest_portal_fetch()
        stmt = (
            select(latest.c.catalogue_service_id, latest.c.target_url, latest.c.last_fetched_at)
            .where(latest.c.last_fetched_at <= cutoff, ~_has_open_fetch(latest))
            .order_by(latest.c.last_fetched_at.asc(), latest.c.catalogue_service_id.asc(), latest.c.target_url.asc())
            .limit(limit)
        )
        return [
            StaleFetchRow(
                catalogue_service_id=row.catalogue_service_id,
                target_url=row.target_url,
                last_fetched_at=row.last_fetched_at,
            )
            for row in self._session.execute(stmt).all()
        ]


def _latest_portal_fetch() -> Subquery:
    """Return one row per portal page: its catalogue row, its URL and the finish time of its newest fetch."""
    return (
        select(
            DiscoveryTask.catalogue_service_id.label("catalogue_service_id"),
            DiscoveryTask.target_url.label("target_url"),
            func.max(DiscoveryFetchLog.fetched_at).label("last_fetched_at"),
        )
        .join(DiscoveryFetchLog, DiscoveryFetchLog.discovery_task_id == DiscoveryTask.id)
        .join(CatalogueService, CatalogueService.id == DiscoveryTask.catalogue_service_id)
        .where(
            DiscoveryTask.kind == DiscoveryTaskKind.FETCH_URL, DiscoveryTask.target_url == CatalogueService.portal_url
        )
        .group_by(DiscoveryTask.catalogue_service_id, DiscoveryTask.target_url)
        .subquery()
    )


def _has_open_fetch(latest: Subquery) -> ColumnElement[bool]:
    """Return whether a fetch_url of the page in ``latest`` is pending or claimed."""
    return exists().where(
        DiscoveryTask.catalogue_service_id == latest.c.catalogue_service_id,
        DiscoveryTask.target_url == latest.c.target_url,
        DiscoveryTask.kind == DiscoveryTaskKind.FETCH_URL,
        DiscoveryTask.status.in_(OPEN_FETCH_STATUSES),
    )
