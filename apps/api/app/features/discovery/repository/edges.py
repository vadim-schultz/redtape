"""Staged requirement edge persistence."""

from __future__ import annotations

from typing import NamedTuple
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import aliased

from app.features.discovery.repository.base import SessionRepository
from app.models.discovery import CatalogueService, DiscoveryCandidateEdge, DiscoveryDocumentCandidate


class EdgeRow(NamedTuple):
    """One edge with its two candidates and the procedure that states it."""

    edge: DiscoveryCandidateEdge
    parent: DiscoveryDocumentCandidate
    required: DiscoveryDocumentCandidate
    procedure: CatalogueService


class EdgeRepository(SessionRepository):
    """Read and write staged ``parent requires required`` edges."""

    def find_edge(
        self, *, parent_candidate_id: UUID, required_candidate_id: UUID, catalogue_service_id: UUID
    ) -> DiscoveryCandidateEdge | None:
        """Return the edge with this unique key, if any."""
        stmt = select(DiscoveryCandidateEdge).where(
            DiscoveryCandidateEdge.parent_candidate_id == parent_candidate_id,
            DiscoveryCandidateEdge.required_candidate_id == required_candidate_id,
            DiscoveryCandidateEdge.catalogue_service_id == catalogue_service_id,
        )
        return self._session.scalar(stmt)

    def add_edge(self, edge: DiscoveryCandidateEdge) -> DiscoveryCandidateEdge:
        """Add ``edge`` to the session and flush it."""
        self._session.add(edge)
        self._session.flush()
        return edge

    def list_candidate_edges(self, candidate_id: UUID) -> list[EdgeRow]:
        """Return the edges that have ``candidate_id`` at either end, oldest first."""
        parent = aliased(DiscoveryDocumentCandidate)
        required = aliased(DiscoveryDocumentCandidate)
        edge = DiscoveryCandidateEdge
        stmt = (
            select(edge, parent, required, CatalogueService)
            .join(parent, parent.id == edge.parent_candidate_id)
            .join(required, required.id == edge.required_candidate_id)
            .join(CatalogueService, CatalogueService.id == edge.catalogue_service_id)
            .where(or_(edge.parent_candidate_id == candidate_id, edge.required_candidate_id == candidate_id))
            .order_by(edge.created_at.asc(), edge.id.asc())
        )
        return [EdgeRow(*row) for row in self._session.execute(stmt).all()]
