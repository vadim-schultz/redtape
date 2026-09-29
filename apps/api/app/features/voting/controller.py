"""Litestar handlers for casting and removing a vote."""

from __future__ import annotations

from uuid import UUID

from litestar import Controller, delete, put
from litestar.exceptions import HTTPException
from litestar.status_codes import HTTP_204_NO_CONTENT, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_409_CONFLICT

from app.features.voting.service import NotFoundError, SelfVoteError, SuggestionNotVotableError, VoteService
from app.models import AppUser
from app.schema.vote import VoteCreate, VoteRead

VOTE_ERROR_STATUS: dict[type[Exception], int] = {
    NotFoundError: HTTP_404_NOT_FOUND,
    SelfVoteError: HTTP_403_FORBIDDEN,
    SuggestionNotVotableError: HTTP_409_CONFLICT,
}


def _to_http(exc: Exception) -> HTTPException:
    return HTTPException(status_code=VOTE_ERROR_STATUS[type(exc)], detail=str(exc))


class VotingController(Controller):
    """Casting and removing a vote on a pending suggestion (Chapter 3)."""

    path = "/"

    @put("/{suggestion_id:uuid}/vote", sync_to_thread=True)
    def cast(self, vote_service: VoteService, current_user: AppUser, suggestion_id: UUID, data: VoteCreate) -> VoteRead:
        try:
            vote = vote_service.cast(suggestion_id=suggestion_id, user_id=current_user.id, value=data.value)
        except (NotFoundError, SelfVoteError, SuggestionNotVotableError) as exc:
            raise _to_http(exc) from exc
        return VoteRead(value=vote.value)

    @delete("/{suggestion_id:uuid}/vote", sync_to_thread=True, status_code=HTTP_204_NO_CONTENT)
    def remove(self, vote_service: VoteService, current_user: AppUser, suggestion_id: UUID) -> None:
        vote_service.remove(suggestion_id=suggestion_id, user_id=current_user.id)
