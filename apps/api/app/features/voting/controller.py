"""Litestar handlers for casting/removing a vote, and moderator overrides of a suggestion's status."""

from __future__ import annotations

from uuid import UUID

from litestar import Controller, delete, get, post, put
from litestar.exceptions import HTTPException
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_204_NO_CONTENT,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)
from pydantic import BaseModel, ConfigDict

from app.features.auth.guards import require_role
from app.features.events.service import EventLogService
from app.features.suggestions.service import AlreadyDecidedError, SuggestionService
from app.features.voting.service import NotFoundError, SelfVoteError, SuggestionNotVotableError, VoteService
from app.models import AppUser
from app.models.suggestion import SuggestionStatus
from app.models.user import UserRole
from app.schema.events import EventRead
from app.schema.suggestion.read import SuggestionRead
from app.schema.vote import VoteCreate, VoteRead

VOTE_ERROR_STATUS: dict[type[Exception], int] = {
    NotFoundError: HTTP_404_NOT_FOUND,
    SelfVoteError: HTTP_403_FORBIDDEN,
    SuggestionNotVotableError: HTTP_409_CONFLICT,
}


def _to_http(exc: Exception) -> HTTPException:
    return HTTPException(status_code=VOTE_ERROR_STATUS[type(exc)], detail=str(exc))


class ModeratorReject(BaseModel):
    """`POST .../reject` body; the reason is optional and never shown on the suggestion itself."""

    model_config = ConfigDict(extra="forbid")

    reason: str | None = None


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

    @post(
        "/{suggestion_id:uuid}/approve",
        sync_to_thread=True,
        status_code=HTTP_200_OK,
        guards=[require_role(UserRole.MODERATOR)],
    )
    def approve(
        self, suggestion_service: SuggestionService, current_user: AppUser, suggestion_id: UUID
    ) -> SuggestionRead:
        return self._override(suggestion_service, suggestion_id, SuggestionStatus.APPROVED, current_user, reason=None)

    @post(
        "/{suggestion_id:uuid}/reject",
        sync_to_thread=True,
        status_code=HTTP_200_OK,
        guards=[require_role(UserRole.MODERATOR)],
    )
    def reject(
        self,
        suggestion_service: SuggestionService,
        current_user: AppUser,
        suggestion_id: UUID,
        data: ModeratorReject | None = None,
    ) -> SuggestionRead:
        reason = data.reason if data else None
        return self._override(suggestion_service, suggestion_id, SuggestionStatus.REJECTED, current_user, reason)

    @get("/{suggestion_id:uuid}/events", sync_to_thread=True, guards=[require_role(UserRole.MODERATOR)])
    def events(self, event_log_service: EventLogService, suggestion_id: UUID) -> list[EventRead]:
        return [EventRead.from_row(event) for event in event_log_service.list_for(suggestion_id)]

    def _override(
        self,
        suggestion_service: SuggestionService,
        suggestion_id: UUID,
        status: SuggestionStatus,
        actor: AppUser,
        reason: str | None,
    ) -> SuggestionRead:
        try:
            suggestion = suggestion_service.transition_to(suggestion_id, status, actor=actor, reason=reason)
        except AlreadyDecidedError as exc:
            raise HTTPException(status_code=HTTP_409_CONFLICT, detail=str(exc)) from exc
        return SuggestionRead.from_row(suggestion, submitter_display_name=None)
