"""Read-only candidate queries for allowlisted operators."""

from __future__ import annotations

from uuid import UUID

from app.features.discovery.lookups import require_candidate
from app.features.discovery.repository import DiscoveryRepository, Page
from app.models.discovery import DiscoveryCandidateStatus
from app.schema.discovery.read import (
    CandidateDetailResponse,
    CandidateListResponse,
    CandidateMentionRead,
    CandidateRead,
)


class CandidateAdminService:
    """Read-only document candidates for allowlisted operators."""

    def __init__(self, repository: DiscoveryRepository) -> None:
        """Bind the service to ``repository``."""
        self._repo = repository

    def list_candidates(
        self, *, status: DiscoveryCandidateStatus | None, offset: int, limit: int
    ) -> CandidateListResponse:
        """Return one page of candidates with mention counts and the total."""
        total = self._repo.count_candidates(status=status)
        rows = self._repo.list_candidates_page(Page(offset=offset, limit=limit), status=status)
        items = [CandidateRead.from_row(row, mention_count=count) for row, count in rows]
        return CandidateListResponse(items=items, total=total, offset=offset, limit=limit)

    def candidate_detail(self, candidate_id: UUID) -> CandidateDetailResponse:
        """Return one candidate with its mentions and their procedures."""
        candidate = require_candidate(self._repo, candidate_id)
        rows = self._repo.list_candidate_mentions(candidate_id)
        mentions = [CandidateMentionRead.from_row(mention, procedure) for mention, procedure in rows]
        return CandidateDetailResponse(
            candidate=CandidateRead.from_row(candidate, mention_count=len(mentions)), mentions=mentions
        )
