"""Record staged requirement edges between candidates that mentions already created."""

from __future__ import annotations

from typing import Literal, TypeGuard, get_args
from uuid import UUID

from app.features.discovery.candidate_key import candidate_key
from app.features.discovery.edge_rows import new_edge, refresh_edge
from app.features.discovery.errors import InvalidDiscoveryInputError
from app.features.discovery.lookups import require_catalogue
from app.features.discovery.repository import DiscoveryRepository
from app.models.discovery import DiscoveryDocumentCandidate
from app.schema.discovery.candidate_edges import (
    CandidateEdgeItem,
    CandidateEdgesRequest,
    CandidateEdgesResponse,
    EdgeSkip,
    EdgeSkipReason,
)

EdgeOutcome = Literal["created", "updated"] | EdgeSkipReason
SKIP_REASONS: tuple[str, ...] = get_args(EdgeSkipReason)


def _is_skip(outcome: EdgeOutcome) -> TypeGuard[EdgeSkipReason]:
    return outcome in SKIP_REASONS


def _tally(outcomes: list[EdgeOutcome]) -> CandidateEdgesResponse:
    skipped = [EdgeSkip(index=i, reason=o) for i, o in enumerate(outcomes) if _is_skip(o)]
    return CandidateEdgesResponse(
        edges_created=outcomes.count("created"),
        edges_updated=outcomes.count("updated"),
        edges_skipped=len(skipped),
        skipped=skipped,
    )


class EdgeService:
    """Stage ``parent requires required`` edges; each item is settled on its own."""

    def __init__(self, repository: DiscoveryRepository) -> None:
        """Bind the service to ``repository``."""
        self._repo = repository

    def record_edges(self, body: CandidateEdgesRequest) -> CandidateEdgesResponse:
        """Record every resolvable edge; an unknown catalogue row rejects the batch before any write."""
        jurisdictions = self._jurisdictions(body.items)
        return _tally([self._record(item, jurisdictions[item.catalogue_service_id]) for item in body.items])

    def _jurisdictions(self, items: list[CandidateEdgeItem]) -> dict[UUID, UUID]:
        ids = {item.catalogue_service_id for item in items}
        return {catalogue_id: require_catalogue(self._repo, catalogue_id).jurisdiction_id for catalogue_id in ids}

    def _record(self, item: CandidateEdgeItem, jurisdiction_id: UUID) -> EdgeOutcome:
        if not item.excerpt.strip():
            return "blank_excerpt"
        parent = self._find(item.parent_title_i18n, jurisdiction_id)
        if parent is None:
            return "unknown_parent"
        required = self._find(item.required_title_i18n, jurisdiction_id)
        if required is None:
            return "unknown_required"
        return "same_endpoints" if parent.id == required.id else self._upsert(item, parent, required)

    def _find(self, title_i18n: dict[str, str], jurisdiction_id: UUID) -> DiscoveryDocumentCandidate | None:
        try:
            key = candidate_key(title_i18n)
        except InvalidDiscoveryInputError:
            return None
        return self._repo.get_candidate_by_key(jurisdiction_id=jurisdiction_id, key=key)

    def _upsert(
        self, item: CandidateEdgeItem, parent: DiscoveryDocumentCandidate, required: DiscoveryDocumentCandidate
    ) -> EdgeOutcome:
        edge = self._repo.find_edge(
            parent_candidate_id=parent.id,
            required_candidate_id=required.id,
            catalogue_service_id=item.catalogue_service_id,
        )
        if edge is not None:
            refresh_edge(edge, item)
            self._repo.flush()
            return "updated"
        self._repo.add_edge(new_edge(item, parent_id=parent.id, required_id=required.id))
        return "created"
