"""Domain logic for casting and removing a vote."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from app.config import settings
from app.features.events.service import EventLogService
from app.features.suggestions.service import SuggestionService
from app.features.voting.repository import VoteRepository
from app.features.voting.thresholds import decide_status
from app.models.suggestion import Suggestion, SuggestionStatus
from app.models.suggestion_event import EventType
from app.models.suggestion_vote import SuggestionVote
from app.schema.suggestion.read import Tally

__all__ = ["NotFoundError", "SelfVoteError", "SuggestionNotVotableError", "VoteService"]


class NotFoundError(ValueError):
    """Raised when the suggestion being voted on does not exist."""


class SuggestionNotVotableError(ValueError):
    """Raised when the suggestion is not `pending`."""


class SelfVoteError(ValueError):
    """Raised when the caller is the suggestion's submitter (D2)."""


class VoteService:
    """Domain logic for casting and removing a vote; the pending-only and no-self-vote rules live here."""

    def __init__(self, repository: VoteRepository, suggestions: SuggestionService, events: EventLogService) -> None:
        self._repo = repository
        self._suggestions = suggestions
        self._events = events

    def cast(self, *, suggestion_id: UUID, user_id: UUID, value: int) -> SuggestionVote:
        suggestion = self._get_suggestion(suggestion_id)
        self._check_pending(suggestion)
        self._check_not_self(suggestion, user_id)
        vote = self._repo.upsert(suggestion_id=suggestion_id, user_id=user_id, value=value)
        self._events.record(suggestion_id, EventType.VOTED, data={"value": value}, actor_user_id=user_id)
        self._maybe_transition(suggestion_id)
        return vote

    def remove(self, *, suggestion_id: UUID, user_id: UUID) -> None:
        self._repo.delete(suggestion_id=suggestion_id, user_id=user_id)

    def tally_for(self, suggestion_id: UUID) -> Tally:
        return self._repo.tally_for(suggestion_id)

    def tally_for_many(self, suggestion_ids: Sequence[UUID]) -> dict[UUID, Tally]:
        return self._repo.tally_for_many(suggestion_ids)

    def my_vote(self, *, suggestion_id: UUID, user_id: UUID) -> int | None:
        vote = self._repo.get(suggestion_id=suggestion_id, user_id=user_id)
        return vote.value if vote else None

    def _get_suggestion(self, suggestion_id: UUID) -> Suggestion:
        suggestion = self._suggestions.get(suggestion_id)
        if suggestion is None:
            raise NotFoundError("suggestion not found")
        return suggestion

    def _check_pending(self, suggestion: Suggestion) -> None:
        if suggestion.status != SuggestionStatus.PENDING:
            raise SuggestionNotVotableError("suggestion is not pending")

    def _check_not_self(self, suggestion: Suggestion, user_id: UUID) -> None:
        if suggestion.submitted_by_user_id == user_id:
            raise SelfVoteError("cannot vote on your own suggestion")

    def _maybe_transition(self, suggestion_id: UUID) -> None:
        """Only casting can cross a threshold (D-open-seam); `remove` never calls this."""
        score = self._repo.tally_for(suggestion_id).score
        new_status = decide_status(score, settings.vote_approve_threshold, settings.vote_reject_threshold)
        if new_status != SuggestionStatus.PENDING:
            self._suggestions.transition_to(suggestion_id, new_status, actor=None)
