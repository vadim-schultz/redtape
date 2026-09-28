from __future__ import annotations

from typing import cast

from litestar import Controller, Request, Response, post
from litestar.exceptions import HTTPException
from litestar.params import Parameter
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_409_CONFLICT, HTTP_422_UNPROCESSABLE_ENTITY

from app.features.auth.principal import Principal
from app.features.suggestions.service import (
    DuplicateSuggestionError,
    MissingSourceUrlError,
    SuggestionService,
    UnknownJurisdictionError,
    UnknownTaxonomyCodeError,
)
from app.features.suggestions.submitter import submitter_display_name, submitter_ref
from app.schema.suggestion.create import SuggestionCreate
from app.schema.suggestion.read import ConflictRead, SuggestionRead

IDEMPOTENCY_KEY_MAX_LENGTH = 128
IDEMPOTENCY_KEY_PATTERN = r"^[\x20-\x7e]+$"

_STATUS_BY_ERROR: dict[type[Exception], int] = {
    DuplicateSuggestionError: HTTP_409_CONFLICT,
    UnknownJurisdictionError: HTTP_422_UNPROCESSABLE_ENTITY,
    UnknownTaxonomyCodeError: HTTP_422_UNPROCESSABLE_ENTITY,
    MissingSourceUrlError: HTTP_422_UNPROCESSABLE_ENTITY,
}


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
        ) as exc:
            raise _to_http(exc) from exc
        read = SuggestionRead.from_row(result.suggestion, submitter_display_name=submitter_display_name(who))
        location = f"{request.url.path.rstrip('/')}/{result.suggestion.id}"
        status_code = HTTP_200_OK if result.replayed else HTTP_201_CREATED
        return Response(read, status_code=status_code, headers={"Location": location})
