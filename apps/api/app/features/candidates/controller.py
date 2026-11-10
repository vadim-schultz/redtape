"""Public, read-only candidate HTTP handlers. There are no ``guards``: anyone may read staged candidates."""

from __future__ import annotations

from uuid import UUID

from litestar import Controller, Response, get
from litestar.params import Parameter
from litestar.status_codes import HTTP_304_NOT_MODIFIED

from app.features.candidates.list_query import PUBLIC_CANDIDATE_SPEC, public_filter_from
from app.features.candidates.screenshot_service import CACHE_CONTROL, ScreenshotReply, ScreenshotService
from app.features.candidates.service import CandidateReadService
from app.features.discovery.repository import Page
from app.features.search.rate_limit import SEARCH_RATE_LIMIT
from app.schema.candidate import CandidateDetail, CandidateListResponse
from app.shared.list_query import ListQuery, provide_list_query
from app.shared.locale import ResolvedLocale
from app.shared.paging import PageParams


def _screenshot_response(reply: ScreenshotReply) -> Response[bytes]:
    """Answer 304 without a body when the client copy is current, else 200 with the stored image."""
    headers = {"ETag": reply.etag, "Cache-Control": CACHE_CONTROL}
    if reply.data is None:
        return Response(b"", status_code=HTTP_304_NOT_MODIFIED, headers=headers)
    return Response(reply.data, media_type=reply.content_type, headers=headers)


class CandidatesController(Controller):
    """Staged document candidates, ranked by completeness (unreviewed model output, D1)."""

    path = "/"
    dependencies = {"list_query": provide_list_query(PUBLIC_CANDIDATE_SPEC)}

    @get("/", sync_to_thread=True, middleware=[SEARCH_RATE_LIMIT.middleware])
    def list_candidates(
        self, candidate_service: CandidateReadService, page: PageParams, locale: ResolvedLocale, list_query: ListQuery
    ) -> CandidateListResponse:
        """Page through the public candidates; with ``q`` ranked by search relevance (throttled), else by confidence."""
        return candidate_service.list_candidates(
            public_filter_from(list_query), Page(offset=page.offset, limit=page.limit), locale
        )

    @get("/{candidate_id:uuid}", sync_to_thread=True)
    def candidate_detail(
        self, candidate_service: CandidateReadService, locale: ResolvedLocale, candidate_id: UUID
    ) -> CandidateDetail:
        """Return the locale-resolved detail of one public candidate."""
        return candidate_service.candidate_detail(candidate_id, locale)

    @get("/{candidate_id:uuid}/screenshot", sync_to_thread=True)
    def candidate_screenshot(
        self,
        candidate_screenshot_service: ScreenshotService,
        candidate_id: UUID,
        if_none_match: str | None = Parameter(header="If-None-Match", default=None),
    ) -> Response[bytes]:
        """Serve a candidate's screenshot, answering 304 when the client's ETag is current."""
        return _screenshot_response(candidate_screenshot_service.serve(candidate_id, if_none_match))
