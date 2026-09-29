from __future__ import annotations

from typing import cast
from uuid import UUID

from litestar import Controller, Request, Response, get, post
from litestar.datastructures import CacheControlHeader
from litestar.exceptions import HTTPException, NotFoundException
from litestar.params import Parameter
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_409_CONFLICT, HTTP_422_UNPROCESSABLE_ENTITY

from app.features.auth.principal import Principal
from app.features.suggestions.service import (
    CycleError,
    DuplicateSuggestionError,
    MissingSourceUrlError,
    SuggestionFilters,
    SuggestionService,
    UnknownDocumentError,
    UnknownJurisdictionError,
    UnknownTaxonomyCodeError,
)
from app.features.suggestions.submitter import submitter_display_name, submitter_ref
from app.features.voting.service import VoteService
from app.models import AppUser
from app.models.suggestion import SuggestionKind, SuggestionSource, SuggestionStatus
from app.schema.suggestion.create import SuggestionCreate
from app.schema.suggestion.read import ConflictRead, SuggestionListResponse, SuggestionRead, Tally

IDEMPOTENCY_KEY_MAX_LENGTH = 128
IDEMPOTENCY_KEY_PATTERN = r"^[\x20-\x7e]+$"
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


class SuggestionsController(Controller):
    """Submission of suggestions by people and crawlers alike (Chapter 6)."""

    path = "/"

    @post("/", sync_to_thread=True, status_code=HTTP_201_CREATED)
    def create(
        self,
        request: Request,
        suggestion_service: SuggestionService,
        principal: object,  # Principal; msgspec can't validate a union of two dataclasses (auth chapter 8)
        data: SuggestionCreate,
        idempotency_key: str | None = Parameter(
            header="Idempotency-Key",
            default=None,
            max_length=IDEMPOTENCY_KEY_MAX_LENGTH,
            pattern=IDEMPOTENCY_KEY_PATTERN,
        ),
    ) -> Response[SuggestionRead]:
        who = cast(Principal, principal)
        try:
            result = suggestion_service.create(
                submitter=submitter_ref(who), request=data, idempotency_key=idempotency_key
            )
        except (
            DuplicateSuggestionError,
            UnknownJurisdictionError,
            UnknownTaxonomyCodeError,
            MissingSourceUrlError,
            UnknownDocumentError,
            CycleError,
        ) as exc:
            raise _to_http(exc) from exc
        read = SuggestionRead.from_row(result.suggestion, submitter_display_name=submitter_display_name(who))
        location = f"{request.url.path.rstrip('/')}/{result.suggestion.id}"
        status_code = HTTP_200_OK if result.replayed else HTTP_201_CREATED
        return Response(read, status_code=status_code, headers={"Location": location})

    @get("/", sync_to_thread=True, cache_control=_NO_CACHE)
    def list_suggestions(
        self,
        suggestion_service: SuggestionService,
        vote_service: VoteService,
        status: list[SuggestionStatus] | None = Parameter(query="status", default=None),
        kind: SuggestionKind | None = Parameter(query="kind", default=None),
        source_type: SuggestionSource | None = Parameter(query="source_type", default=None),
        jurisdiction_id: UUID | None = Parameter(query="jurisdiction_id", default=None),
        offset: int = Parameter(query="offset", default=0, ge=0),
        limit: int = Parameter(query="limit", default=20, ge=1, le=100),
    ) -> SuggestionListResponse:
        filters = SuggestionFilters(
            status=tuple(status or ()), kind=kind, source_type=source_type, jurisdiction_id=jurisdiction_id
        )
        result = suggestion_service.list_suggestions(filters=filters, offset=offset, limit=limit)
        tallies = vote_service.tally_for_many([item.id for item in result.items])
        items = [with_tally(item, tally=tallies[item.id]) for item in result.items]
        return SuggestionListResponse(items=items, total=result.total, offset=result.offset, limit=result.limit)

    @get("/{suggestion_id:uuid}", sync_to_thread=True, cache_control=_NO_CACHE)
    def get_suggestion(
        self,
        suggestion_service: SuggestionService,
        vote_service: VoteService,
        suggestion_id: UUID,
        optional_user: AppUser | None,
    ) -> SuggestionRead:
        read = suggestion_service.get_suggestion(suggestion_id)
        if read is None:
            raise NotFoundException("Suggestion not found")
        tally = vote_service.tally_for(suggestion_id)
        my_vote = vote_service.my_vote(suggestion_id=suggestion_id, user_id=optional_user.id) if optional_user else None
        return with_tally(read, tally=tally, my_vote=my_vote)
