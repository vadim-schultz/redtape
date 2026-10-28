"""Build and refresh staged edge rows from validated batch items."""

from __future__ import annotations

from uuid import UUID

from app.models.discovery import DiscoveryCandidateEdge
from app.schema.discovery.candidate_edges import CandidateEdgeItem


def new_edge(item: CandidateEdgeItem, *, parent_id: UUID, required_id: UUID) -> DiscoveryCandidateEdge:
    """Return an unsaved edge from ``parent_id`` to ``required_id`` for ``item``."""
    edge = DiscoveryCandidateEdge(
        parent_candidate_id=parent_id,
        required_candidate_id=required_id,
        catalogue_service_id=item.catalogue_service_id,
    )
    refresh_edge(edge, item)
    return edge


def refresh_edge(edge: DiscoveryCandidateEdge, item: CandidateEdgeItem) -> None:
    """Overwrite everything a re-run may change; the key columns stay."""
    edge.basis = item.basis
    edge.condition = item.condition
    edge.is_optional = item.is_optional
    edge.excerpt = item.excerpt
    edge.extractor = item.extractor
    edge.extractor_version = item.extractor_version
