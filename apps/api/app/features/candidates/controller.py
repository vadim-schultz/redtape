"""Public, read-only candidate HTTP handlers. There are no ``guards``: anyone may read staged candidates."""

from __future__ import annotations

from uuid import UUID

from litestar import Controller, get

from app.features.candidates.list_query import PUBLIC_CANDIDATE_SPEC, public_filter_from
from app.features.candidates.service import CandidateReadService
from app.features.discovery.repository import Page
from app.schema.candidate import CandidateDetail, CandidateListResponse
from app.shared.list_query import ListQuery, provide_list_query
from app.shared.locale import ResolvedLocale
from app.shared.paging import PageParams


class CandidatesController(Controller):
    """Staged document candidates, ranked by completeness (unreviewed model output, D1)."""

    path = "/"
    dependencies = {"list_query": provide_list_query(PUBLIC_CANDIDATE_SPEC)}

    @get("/", sync_to_thread=True)
    def list_candidates(
        self, candidate_service: CandidateReadService, page: PageParams, locale: ResolvedLocale, list_query: ListQuery
    ) -> CandidateListResponse:
        return candidate_service.list_candidates(
            public_filter_from(list_query), Page(offset=page.offset, limit=page.limit), locale
        )

    @get("/{candidate_id:uuid}", sync_to_thread=True)
    def candidate_detail(
        self, candidate_service: CandidateReadService, locale: ResolvedLocale, candidate_id: UUID
    ) -> CandidateDetail:
        return candidate_service.candidate_detail(candidate_id, locale)
