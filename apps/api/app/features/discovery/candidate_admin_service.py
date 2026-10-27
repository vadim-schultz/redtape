"""Read-only candidate queries for allowlisted operators."""

from __future__ import annotations

from uuid import UUID

from app.features.discovery.lookups import require_candidate
from app.features.discovery.repository import CandidateFilter, DiscoveryRepository, Page
from app.features.discovery.repository.candidate_listing import CandidateListRow
from app.models.discovery import DiscoveryMentionRole
from app.schema.discovery.read import (
    CandidateDetailResponse,
    CandidateListItemRead,
    CandidateListResponse,
    CandidateMentionRead,
    CandidateRead,
)


def _list_item(row: CandidateListRow) -> CandidateListItemRead:
    base = CandidateRead.from_row(row.candidate, mention_count=row.mention_count)
    return CandidateListItemRead(
        **base.model_dump(),
        roles=[DiscoveryMentionRole(role) for role in row.roles],
        jurisdiction_name_i18n=row.jurisdiction_name_i18n,
    )


class CandidateAdminService:
    """Read-only document candidates for allowlisted operators."""

    def __init__(self, repository: DiscoveryRepository) -> None:
        """Bind the service to ``repository``."""
        self._repo = repository

    def list_candidates(self, candidate_filter: CandidateFilter, page: Page) -> CandidateListResponse:
        """Return one page of matching candidates with mention counts and the total."""
        total = self._repo.count_candidates(candidate_filter)
        rows = self._repo.list_candidates_page(page, candidate_filter)
        items = [_list_item(row) for row in rows]
        return CandidateListResponse(items=items, total=total, offset=page.offset, limit=page.limit)

    def candidate_detail(self, candidate_id: UUID) -> CandidateDetailResponse:
        """Return one candidate with its jurisdiction name, mentions, procedures and artifact summaries."""
        candidate = require_candidate(self._repo, candidate_id)
        rows = self._repo.list_candidate_mentions(candidate_id)
        mentions = [CandidateMentionRead.from_row(*row) for row in rows]
        return CandidateDetailResponse(
            candidate=CandidateRead.from_row(candidate, mention_count=len(mentions)),
            jurisdiction_name_i18n=self._repo.get_jurisdiction_name_i18n(candidate.jurisdiction_id),
            mentions=mentions,
        )
