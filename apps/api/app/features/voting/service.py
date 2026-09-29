"""Domain logic for casting and removing a vote."""

from __future__ import annotations

from uuid import UUID

from app.features.suggestions.service import SuggestionService
from app.features.voting.repository import VoteRepository
from app.models.suggestion import Suggestion, SuggestionStatus
from app.models.suggestion_vote import SuggestionVote

__all__ = ["NotFoundError", "SelfVoteError", "SuggestionNotVotableError", "VoteService"]


class NotFoundError(ValueError):
    """Raised when the suggestion being voted on does not exist."""


class SuggestionNotVotableError(ValueError):
    """Raised when the suggestion is not `pending`."""


class SelfVoteError(ValueError):
    """Raised when the caller is the suggestion's submitter (D2)."""


class VoteService:
    """Domain logic for casting and removing a vote; the pending-only and no-self-vote rules live here."""

    def __init__(self, repository: VoteRepository, suggestions: SuggestionService) -> None:
        self._repo = repository
        self._suggestions = suggestions

    def cast(self, *, suggestion_id: UUID, user_id: UUID, value: int) -> SuggestionVote:
        suggestion = self._get_suggestion(suggestion_id)
        self._check_pending(suggestion)
        self._check_not_self(suggestion, user_id)
        return self._repo.upsert(suggestion_id=suggestion_id, user_id=user_id, value=value)

    def remove(self, *, suggestion_id: UUID, user_id: UUID) -> None:
        self._repo.delete(suggestion_id=suggestion_id, user_id=user_id)

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
