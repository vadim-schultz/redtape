"""Domain logic for casting and removing a vote, and why a threshold-crossing cast did not decide."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from app.config import settings
from app.features.events.service import EventLogService
from app.features.suggestions.service import PromotionConflictError, SuggestionService
from app.features.voting.repository import VoteRepository
from app.features.voting.thresholds import decide_status
from app.models.suggestion import Suggestion, SuggestionStatus
from app.models.suggestion_event import EventType
from app.models.suggestion_vote import SuggestionVote
from app.schema.suggestion.read import Tally

__all__ = ["CastResult", "NotFoundError", "SelfVoteError", "SuggestionNotVotableError", "VoteService"]


class NotFoundError(ValueError):
    """Raised when the suggestion being voted on does not exist."""


class SuggestionNotVotableError(ValueError):
    """Raised when the suggestion is not `pending`."""


class SelfVoteError(ValueError):
    """Raised when the caller is the suggestion's submitter (D2)."""


@dataclass(frozen=True, slots=True)
class CastResult:
    """Outcome of casting a vote: the stored vote, and why the suggestion was not decided if a threshold was crossed."""

    vote: SuggestionVote
    promotion_blocked: str | None = None


class VoteService:
    """Domain logic for casting and removing a vote; the pending-only and no-self-vote rules live here."""

    def __init__(self, repository: VoteRepository, suggestions: SuggestionService, events: EventLogService) -> None:
        """Bind the service to its vote repository, suggestion service and event log."""
        self._repo = repository
        self._suggestions = suggestions
        self._events = events

    def cast(self, *, suggestion_id: UUID, user_id: UUID, value: int) -> CastResult:
        """Record or change a vote on a pending suggestion, then promote the suggestion if a threshold is crossed."""
        suggestion = self._get_suggestion(suggestion_id)
        self._check_pending(suggestion)
        self._check_not_self(suggestion, user_id)
        vote = self._repo.upsert(suggestion_id=suggestion_id, user_id=user_id, value=value)
        self._events.record(suggestion_id, EventType.VOTED, data={"value": value}, actor_user_id=user_id)
        blocked = self._maybe_transition(suggestion_id)
        return CastResult(vote=vote, promotion_blocked=blocked)

    def remove(self, *, suggestion_id: UUID, user_id: UUID) -> None:
        """Delete the caller's vote on a pending suggestion; a threshold crossing is never re-evaluated here."""
        suggestion = self._get_suggestion(suggestion_id)
        self._check_pending(suggestion)
        self._repo.delete(suggestion_id=suggestion_id, user_id=user_id)

    def tally_for(self, suggestion_id: UUID) -> Tally:
        """Return the vote tally of one suggestion."""
        return self._repo.tally_for(suggestion_id)

    def tally_for_many(self, suggestion_ids: Sequence[UUID]) -> dict[UUID, Tally]:
        """Return the vote tally of each suggestion in one query."""
        return self._repo.tally_for_many(suggestion_ids)

    def my_vote(self, *, suggestion_id: UUID, user_id: UUID) -> int | None:
        """Return the caller's vote value on a suggestion, or None if they have not voted."""
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

    def _maybe_transition(self, suggestion_id: UUID) -> str | None:
        """
        Only casting can cross a threshold (D-open-seam); `remove` never calls this.

        A blocked promotion is reported as data, not raised: an exception here would reach
        `provide_session` and roll back the vote just recorded above (C1).
        """
        score = self._repo.tally_for(suggestion_id).score
        new_status = decide_status(score, settings.vote_approve_threshold, settings.vote_reject_threshold)
        if new_status == SuggestionStatus.PENDING:
            return None
        try:
            self._suggestions.transition_to(suggestion_id, new_status, actor=None)
        except PromotionConflictError as exc:
            return str(exc)
        return None
