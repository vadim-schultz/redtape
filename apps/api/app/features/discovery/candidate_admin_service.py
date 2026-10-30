"""Read-only candidate queries for allowlisted operators."""

from __future__ import annotations

from dataclasses import asdict
from urllib.parse import urlparse
from uuid import UUID

from app.features.discovery.candidate_list_items import list_item, reject_unknown_codes
from app.features.discovery.candidate_tags import candidate_tag_suggestions
from app.features.discovery.lookups import require_candidate
from app.features.discovery.repository import (
    CandidateFilter,
    CandidateSourceFilter,
    CandidateSourceRow,
    DiscoveryRepository,
    EdgeRow,
    Page,
)
from app.features.taxonomy.service import TaxonomyService
from app.schema.discovery.candidate_edges import CandidateEdgeListResponse, CandidateEdgeRead
from app.schema.discovery.candidate_sources import CandidateSourceListResponse, CandidateSourceRead
from app.schema.discovery.read import (
    CandidateDetailResponse,
    CandidateListResponse,
    CandidateMentionRead,
    CandidateRead,
    TagSupportRead,
)


def _source_read(row: CandidateSourceRow) -> CandidateSourceRead:
    host = (urlparse(row.source_url).hostname or "").lower()
    return CandidateSourceRead(**asdict(row), host=host)


def _edge_read(row: EdgeRow) -> CandidateEdgeRead:
    return CandidateEdgeRead(
        id=row.edge.id,
        parent_candidate_id=row.parent.id,
        parent_title_i18n=row.parent.title_i18n,
        required_candidate_id=row.required.id,
        required_title_i18n=row.required.title_i18n,
        catalogue_service_id=row.procedure.id,
        procedure_title_i18n=row.procedure.title_i18n,
        basis=row.edge.basis,
        condition=row.edge.condition,
        is_optional=row.edge.is_optional,
        excerpt=row.edge.excerpt,
        extractor=row.edge.extractor,
        extractor_version=row.edge.extractor_version,
        created_at=row.edge.created_at,
    )


class CandidateAdminService:
    """Read-only document candidates for allowlisted operators."""

    def __init__(self, repository: DiscoveryRepository, taxonomy: TaxonomyService) -> None:
        """Bind the service to ``repository`` and the taxonomy lookups."""
        self._repo = repository
        self._taxonomy = taxonomy

    def list_candidates(self, candidate_filter: CandidateFilter, page: Page) -> CandidateListResponse:
        """Return one page of matching candidates with counts, completeness and the total.

        An unknown taxonomy code in the filter is a validation error.
        """
        reject_unknown_codes(candidate_filter.completeness, self._taxonomy)
        total = self._repo.count_candidates(candidate_filter)
        rows = self._repo.list_candidates_page(page, candidate_filter)
        done = self._repo.completeness_for([row.candidate.id for row in rows])
        items = [list_item(row, done[row.candidate.id]) for row in rows]
        return CandidateListResponse(items=items, total=total, offset=page.offset, limit=page.limit)

    def list_candidate_sources(
        self, candidate_filter: CandidateSourceFilter, page: Page
    ) -> CandidateSourceListResponse:
        """Return one page of procedures with candidate mentions and the snapshot page to capture."""
        found = self._repo.list_candidate_sources(candidate_filter, page)
        items = [_source_read(row) for row in found.items]
        return CandidateSourceListResponse(items=items, total=found.total, offset=page.offset, limit=page.limit)

    def candidate_detail(self, candidate_id: UUID) -> CandidateDetailResponse:
        """Return one candidate with its jurisdiction name, mentions, procedures and artifact summaries."""
        candidate = require_candidate(self._repo, candidate_id)
        rows = self._repo.list_candidate_mentions(candidate_id)
        mentions = [CandidateMentionRead.from_row(*row) for row in rows]
        suggestions = candidate_tag_suggestions(row.mention for row in rows)
        return CandidateDetailResponse(
            candidate=CandidateRead.from_row(candidate, mention_count=len(mentions)),
            jurisdiction_name_i18n=self._repo.get_jurisdiction_name_i18n(candidate.jurisdiction_id),
            mentions=mentions,
            suggested_domain_codes=[TagSupportRead(**s._asdict()) for s in suggestions.domains],
            suggested_situation_codes=[TagSupportRead(**s._asdict()) for s in suggestions.situations],
        )

    def candidate_edges(self, candidate_id: UUID) -> CandidateEdgeListResponse:
        """Return every staged edge that has the candidate as its parent or its required end."""
        require_candidate(self._repo, candidate_id)
        return CandidateEdgeListResponse(
            items=[_edge_read(row) for row in self._repo.list_candidate_edges(candidate_id)]
        )
