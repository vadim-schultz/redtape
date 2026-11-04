"""HTTP endpoints for submitting, listing and reading suggestions; domain errors become HTTP statuses here."""

from __future__ import annotations

from uuid import UUID

from litestar import Controller, Response, get, post
from litestar.datastructures import CacheControlHeader
from litestar.exceptions import HTTPException, NotFoundException
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_409_CONFLICT, HTTP_422_UNPROCESSABLE_ENTITY

from app.features.suggestions.query import SuggestionListQuery
from app.features.suggestions.service import (
    CycleError,
    DuplicateSuggestionError,
    MissingSourceUrlError,
    SubmissionResult,
    SuggestionService,
    UnknownDocumentError,
    UnknownJurisdictionError,
    UnknownTaxonomyCodeError,
)
from app.features.suggestions.submission import Submission
from app.features.voting.service import VoteService
from app.models import AppUser
from app.schema.suggestion.create import SuggestionCreate
from app.schema.suggestion.read import ConflictRead, SuggestionListResponse, SuggestionRead, Tally

_NO_CACHE = CacheControlHeader(no_cache=True)

_STATUS_BY_ERROR: dict[type[Exception], int] = {
    DuplicateSuggestionError: HTTP_409_CONFLICT,
    UnknownJurisdictionError: HTTP_422_UNPROCESSABLE_ENTITY,
    UnknownTaxonomyCodeError: HTTP_422_UNPROCESSABLE_ENTITY,
    MissingSourceUrlError: HTTP_422_UNPROCESSABLE_ENTITY,
    UnknownDocumentError: HTTP_422_UNPROCESSABLE_ENTITY,
    CycleError: HTTP_422_UNPROCESSABLE_ENTITY,
}


def with_tally(read: SuggestionRead, *, tally: Tally, my_vote: int | None = None) -> SuggestionRead:
    """Compose voting data into a suggestion response (controller-level composition, like the matrix endpoint)."""
    return read.model_copy(update={"tally": tally, "my_vote": my_vote})


def _to_http(exc: Exception) -> HTTPException:
    if isinstance(exc, DuplicateSuggestionError):
        conflicts = [ConflictRead(type=c.type, id=c.id).model_dump(mode="json") for c in exc.conflicts]
        return HTTPException(
            status_code=HTTP_409_CONFLICT, detail="Duplicate suggestion", extra={"conflicts": conflicts}
        )
    return HTTPException(status_code=_STATUS_BY_ERROR[type(exc)], detail=str(exc))


_DOMAIN_ERRORS = tuple(_STATUS_BY_ERROR)


def _created_response(result: SubmissionResult, submission: Submission) -> Response[SuggestionRead]:
    read = SuggestionRead.from_row(result.suggestion, submitter_display_name=submission.display_name)
    location = f"{submission.collection_path}/{result.suggestion.id}"
    status_code = HTTP_200_OK if result.replayed else HTTP_201_CREATED
    return Response(read, status_code=status_code, headers={"Location": location})


def _with_tallies(result: SuggestionListResponse, vote_service: VoteService) -> SuggestionListResponse:
    tallies = vote_service.tally_for_many([item.id for item in result.items])
    items = [with_tally(item, tally=tallies[item.id]) for item in result.items]
    return SuggestionListResponse(items=items, total=result.total, offset=result.offset, limit=result.limit)


class SuggestionsController(Controller):
    """Submission of suggestions by people and crawlers alike (Chapter 6)."""

    path = "/"

    @post("/", sync_to_thread=True, status_code=HTTP_201_CREATED)
    def create(
        self, suggestion_service: SuggestionService, data: SuggestionCreate, submission: Submission
    ) -> Response[SuggestionRead]:
        """Store a pending suggestion (201), or answer an idempotent replay with the earlier row (200)."""
        try:
            result = suggestion_service.create(
                submitter=submission.submitter, request=data, idempotency_key=submission.idempotency_key
            )
        except _DOMAIN_ERRORS as exc:
            raise _to_http(exc) from exc
        return _created_response(result, submission)

    @get("/", sync_to_thread=True, cache_control=_NO_CACHE)
    def list_suggestions(
        self, suggestion_service: SuggestionService, vote_service: VoteService, suggestion_query: SuggestionListQuery
    ) -> SuggestionListResponse:
        """Page through suggestions, each with its vote tally attached."""
        page = suggestion_query.page
        result = suggestion_service.list_suggestions(
            filters=suggestion_query.filters, offset=page.offset, limit=page.limit
        )
        return _with_tallies(result, vote_service)

    @get("/{suggestion_id:uuid}", sync_to_thread=True, cache_control=_NO_CACHE)
    def get_suggestion(
        self,
        suggestion_service: SuggestionService,
        vote_service: VoteService,
        suggestion_id: UUID,
        optional_user: AppUser | None,
    ) -> SuggestionRead:
        """Return one suggestion with its tally and the caller's own vote; 404 when it does not exist."""
        read = suggestion_service.get_suggestion(suggestion_id)
        if read is None:
            raise NotFoundException("Suggestion not found")
        tally = vote_service.tally_for(suggestion_id)
        my_vote = vote_service.my_vote(suggestion_id=suggestion_id, user_id=optional_user.id) if optional_user else None
        return with_tally(read, tally=tally, my_vote=my_vote)
