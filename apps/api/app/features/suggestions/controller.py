from __future__ import annotations

from litestar import Controller, Response, post
from litestar.exceptions import HTTPException

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
    DuplicateSuggestionError: 409,
    UnknownJurisdictionError: 422,
    UnknownTaxonomyCodeError: 422,
}


def _to_http(exc: Exception) -> HTTPException:
    if isinstance(exc, DuplicateSuggestionError):
        conflicts = [ConflictRead(type=c.type, id=c.id).model_dump(mode="json") for c in exc.conflicts]
        return HTTPException(status_code=409, detail="Duplicate suggestion", extra={"conflicts": conflicts})
    return HTTPException(status_code=_STATUS_BY_ERROR[type(exc)], detail=str(exc))


class SuggestionsController(Controller):
    """Human submission of suggestions (Chapter 5); machine principals arrive in Chapter 6."""

    path = "/"

    @post("/", sync_to_thread=True, status_code=201)
    def create(
        self,
        suggestion_service: SuggestionService,
        current_user: AppUser,
        data: SuggestionCreate,
    ) -> Response[SuggestionRead]:
        try:
            suggestion = suggestion_service.create(submitter=SubmitterRef("user", current_user.id), request=data)
        except (DuplicateSuggestionError, UnknownJurisdictionError, UnknownTaxonomyCodeError) as exc:
            raise _to_http(exc) from exc
        read = SuggestionRead.from_row(suggestion, submitter_display_name=current_user.display_name)
        return Response(read, status_code=201, headers={"Location": f"/api/v1/suggestions/{suggestion.id}"})
