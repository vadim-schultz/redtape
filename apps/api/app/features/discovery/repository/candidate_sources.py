"""Catalogue rows that carry candidate mentions, with the page a screenshot of them should capture."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import ColumnElement, Select, exists, func, select
from sqlalchemy.orm import aliased
from sqlalchemy.sql import Subquery

from app.features.discovery.repository.base import SessionRepository
from app.features.discovery.repository.candidate_source_filter import CandidateSourceFilter
from app.features.discovery.repository.task_listing import Page
from app.models.discovery import DiscoveryArtifact, DiscoveryArtifactKind, DiscoveryCandidateMention


@dataclass(frozen=True, slots=True)
class CandidateSourceRow:
    """One mentioned procedure: the newest snapshot url, whether it has a screenshot, and its mention count."""

    catalogue_service_id: UUID
    source_url: str
    has_screenshot: bool
    mention_count: int


@dataclass(frozen=True, slots=True)
class CandidateSourceRows:
    """One page of sources and the total of the filtered result."""

    items: list[CandidateSourceRow]
    total: int


def _mention_counts() -> Subquery:
    count = func.count(DiscoveryCandidateMention.id).label("mention_count")
    return (
        select(DiscoveryCandidateMention.catalogue_service_id, count)
        .group_by(DiscoveryCandidateMention.catalogue_service_id)
        .subquery()
    )


def _newest_snapshots() -> Subquery:
    return (
        select(DiscoveryArtifact.catalogue_service_id, DiscoveryArtifact.source_url)
        .where(DiscoveryArtifact.kind == DiscoveryArtifactKind.HTML_SNAPSHOT)
        .distinct(DiscoveryArtifact.catalogue_service_id)
        .order_by(
            DiscoveryArtifact.catalogue_service_id, DiscoveryArtifact.fetched_at.desc(), DiscoveryArtifact.id.desc()
        )
        .subquery()
    )


def _screenshot_exists(procedure_id: ColumnElement[UUID]) -> ColumnElement[bool]:
    shot = aliased(DiscoveryArtifact)
    return exists().where(shot.catalogue_service_id == procedure_id, shot.kind == DiscoveryArtifactKind.SCREENSHOT)


def _sources_stmt(candidate_filter: CandidateSourceFilter) -> Select:
    counts, snapshots = _mention_counts(), _newest_snapshots()
    procedure = counts.c.catalogue_service_id
    has_screenshot = _screenshot_exists(procedure)
    columns = (procedure, snapshots.c.source_url, has_screenshot.label("has_screenshot"), counts.c.mention_count)
    return (
        select(*columns)
        .join(snapshots, snapshots.c.catalogue_service_id == procedure)
        .where(*candidate_filter.conditions(procedure, snapshots.c.source_url, has_screenshot))
    )


class CandidateSourceRepository(SessionRepository):
    """List the procedures candidates were found on, for the screenshot requeue tool."""

    def list_candidate_sources(self, candidate_filter: CandidateSourceFilter, page: Page) -> CandidateSourceRows:
        """Return one page of mentioned procedures with a snapshot, busiest first, and the filtered total."""
        stmt = _sources_stmt(candidate_filter)
        total = int(self._session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
        ordered = stmt.order_by(stmt.selected_columns.mention_count.desc(), stmt.selected_columns.catalogue_service_id)
        rows = self._session.execute(ordered.offset(page.offset).limit(page.limit)).all()
        return CandidateSourceRows(items=[CandidateSourceRow(*row) for row in rows], total=total)
