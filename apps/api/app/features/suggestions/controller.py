from __future__ import annotations

from litestar import Controller, Request, Response, post
from litestar.exceptions import HTTPException
from litestar.status_codes import HTTP_201_CREATED, HTTP_409_CONFLICT, HTTP_422_UNPROCESSABLE_ENTITY

from app.features.suggestions.service import (
    DuplicateSuggestionError,
    SubmitterRef,
    SuggestionService,
    UnknownJurisdictionError,
    UnknownTaxonomyCodeError,
)
from app.models.user import AppUser
from app.schema.suggestion.create import SuggestionCreate
from app.schema.suggestion.read import ConflictRead, SuggestionRead

_STATUS_BY_ERROR: dict[type[Exception], int] = {
    DuplicateSuggestionError: HTTP_409_CONFLICT,
    UnknownJurisdictionError: HTTP_422_UNPROCESSABLE_ENTITY,
    UnknownTaxonomyCodeError: HTTP_422_UNPROCESSABLE_ENTITY,
}


def _to_http(exc: Exception) -> HTTPException:
    if isinstance(exc, DuplicateSuggestionError):
        conflicts = [ConflictRead(type=c.type, id=c.id).model_dump(mode="json") for c in exc.conflicts]
        return HTTPException(
            status_code=HTTP_409_CONFLICT, detail="Duplicate suggestion", extra={"conflicts": conflicts}
        )
    return HTTPException(status_code=_STATUS_BY_ERROR[type(exc)], detail=str(exc))


class SuggestionsController(Controller):
    """Human submission of suggestions (Chapter 5); machine principals arrive in Chapter 6."""

    path = "/"

    @post("/", sync_to_thread=True, status_code=HTTP_201_CREATED)
    def create(
        self,
        request: Request,
        suggestion_service: SuggestionService,
        current_user: AppUser,
        data: SuggestionCreate,
    ) -> Response[SuggestionRead]:
        try:
            suggestion = suggestion_service.create(submitter=SubmitterRef("user", current_user.id), request=data)
        except (DuplicateSuggestionError, UnknownJurisdictionError, UnknownTaxonomyCodeError) as exc:
            raise _to_http(exc) from exc
        read = SuggestionRead.from_row(suggestion, submitter_display_name=current_user.display_name)
        location = f"{request.url.path.rstrip('/')}/{suggestion.id}"
        return Response(read, status_code=HTTP_201_CREATED, headers={"Location": location})
