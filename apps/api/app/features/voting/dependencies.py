"""Dependency providers for the voting feature."""

from __future__ import annotations

from litestar.di import Provide
from sqlalchemy.orm import Session

from app.features.events.service import EventLogService
from app.features.suggestions.dependencies import router_dependencies as suggestion_dependencies
from app.features.suggestions.service import SuggestionService
from app.features.voting.repository import VoteRepository
from app.features.voting.service import VoteService


def provide_vote_repository(session: Session) -> VoteRepository:
    """Bind a vote repository to the request session."""
    return VoteRepository(session)


def provide_vote_service(
    vote_repository: VoteRepository, suggestion_service: SuggestionService, event_log_service: EventLogService
) -> VoteService:
    """Bind the vote service to its repository, the suggestion service and the event log."""
    return VoteService(vote_repository, suggestion_service, event_log_service)


router_dependencies = {
    **suggestion_dependencies,
    "vote_repository": Provide(provide_vote_repository, sync_to_thread=False),
    "vote_service": Provide(provide_vote_service, sync_to_thread=False),
}
