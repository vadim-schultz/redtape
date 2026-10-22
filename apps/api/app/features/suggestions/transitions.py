"""Suggestion status transitions: the one place `status` changes (D5)."""

from __future__ import annotations

from uuid import UUID

from app.features.events.service import EventLogService
from app.features.suggestions.handlers import KindHandler
from app.features.suggestions.repository import SuggestionRepository
from app.models.suggestion import Suggestion, SuggestionKind, SuggestionStatus
from app.models.suggestion_event import EventType
from app.models.user import AppUser

_PROMOTED_TABLE = {SuggestionKind.NEW_DOCUMENT: "document", SuggestionKind.NEW_REQUIREMENT: "document_requirement"}


class AlreadyDecidedError(ValueError):
    """Raised when transitioning a suggestion that is already approved or rejected (D6)."""


def _actor_id(actor: AppUser | None) -> UUID | None:
    return actor.id if actor else None


class SuggestionTransitions:
    """Move a pending suggestion to approved or rejected, promoting on approval."""

    def __init__(
        self,
        repository: SuggestionRepository,
        handlers: dict[SuggestionKind, KindHandler],
        events: EventLogService,
    ) -> None:
        """Bind the transitions to storage, per-kind handlers and the event log."""
        self._repo = repository
        self._handlers = handlers
        self._events = events

    def transition_to(
        self, suggestion_id: UUID, new_status: SuggestionStatus, actor: AppUser | None, reason: str | None = None
    ) -> Suggestion:
        """Pending is idempotent; approved/rejected are terminal (D6)."""
        suggestion = self._get_pending(suggestion_id)
        if new_status == SuggestionStatus.PENDING:
            return suggestion
        old_status = suggestion.status
        if new_status == SuggestionStatus.APPROVED:
            self._promote_and_log(suggestion, actor)
        suggestion.status = new_status
        self._log_status_change(suggestion_id, old_status, new_status, actor)
        return self._repo.save(suggestion)

    def _get_pending(self, suggestion_id: UUID) -> Suggestion:
        suggestion = self._repo.get(suggestion_id)
        if suggestion is None:
            raise ValueError(f"suggestion {suggestion_id} not found")
        if suggestion.status != SuggestionStatus.PENDING:
            raise AlreadyDecidedError(f"suggestion {suggestion_id} is already {suggestion.status}")
        return suggestion

    def _promote_and_log(self, suggestion: Suggestion, actor: AppUser | None) -> None:
        created_id = self._handlers[suggestion.kind].promote(suggestion)
        data = {"created_id": str(created_id), "table": _PROMOTED_TABLE[suggestion.kind]}
        self._events.record(suggestion.id, EventType.PROMOTED, data=data, actor_user_id=_actor_id(actor))

    def _log_status_change(
        self, suggestion_id: UUID, old_status: SuggestionStatus, new_status: SuggestionStatus, actor: AppUser | None
    ) -> None:
        data = {"from": old_status.value, "to": new_status.value}
        self._events.record(suggestion_id, EventType.STATUS_CHANGED, data=data, actor_user_id=_actor_id(actor))
