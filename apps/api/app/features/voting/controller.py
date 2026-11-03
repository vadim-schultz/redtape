"""Litestar handlers for casting and removing a vote."""

from __future__ import annotations

from uuid import UUID

from litestar import Controller, Response, delete, put
from litestar.exceptions import HTTPException
from litestar.status_codes import HTTP_204_NO_CONTENT, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT

from app.features.suggestions.service import AlreadyDecidedError, SuggestionNotFoundError
from app.features.voting.service import CastResult, NotFoundError, SelfVoteError, SuggestionNotVotableError, VoteService
from app.models import AppUser
from app.schema.vote import VoteCreate, VoteRead

VOTE_ERROR_STATUS: dict[type[Exception], int] = {
    NotFoundError: HTTP_404_NOT_FOUND,
    SelfVoteError: HTTP_403_FORBIDDEN,
    SuggestionNotVotableError: HTTP_409_CONFLICT,
    AlreadyDecidedError: HTTP_409_CONFLICT,
    SuggestionNotFoundError: HTTP_404_NOT_FOUND,
}

_DOMAIN_ERRORS = tuple(VOTE_ERROR_STATUS)


def _to_http(exc: Exception) -> HTTPException:
    return HTTPException(status_code=VOTE_ERROR_STATUS[type(exc)], detail=str(exc))


def _blocked_response(result: CastResult) -> Response[dict[str, object]]:
    """A kept vote whose promotion was blocked: 409, shaped like a raised `HTTPException` (C1)."""
    body: dict[str, object] = {
        "status_code": HTTP_409_CONFLICT,
        "detail": result.promotion_blocked,
        "extra": {"value": result.vote.value},
    }
    return Response(body, status_code=HTTP_409_CONFLICT)


class VotingController(Controller):
    """Casting and removing a vote on a pending suggestion (Chapter 3)."""

    path = "/"

    @put("/{suggestion_id:uuid}/vote", sync_to_thread=True)
    def cast(
        self, vote_service: VoteService, current_user: AppUser, suggestion_id: UUID, data: VoteCreate
    ) -> VoteRead | Response[dict[str, object]]:
        try:
            result = vote_service.cast(suggestion_id=suggestion_id, user_id=current_user.id, value=data.value)
        except _DOMAIN_ERRORS as exc:
            raise _to_http(exc) from exc
        if result.promotion_blocked is not None:
            return _blocked_response(result)
        return VoteRead(value=result.vote.value)

    @delete("/{suggestion_id:uuid}/vote", sync_to_thread=True, status_code=HTTP_204_NO_CONTENT)
    def remove(self, vote_service: VoteService, current_user: AppUser, suggestion_id: UUID) -> None:
        try:
            vote_service.remove(suggestion_id=suggestion_id, user_id=current_user.id)
        except _DOMAIN_ERRORS as exc:
            raise _to_http(exc) from exc
