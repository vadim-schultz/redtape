"""Test composition of the suggestion service from its collaborators."""

from __future__ import annotations

from app.features.documents.promotion import PromotionPort
from app.features.events.service import EventLogService
from app.features.suggestions.handlers import HandlerDeps, build_dispatch
from app.features.suggestions.repository import SuggestionRepository
from app.features.suggestions.service import SuggestionService
from app.features.suggestions.transitions import SuggestionTransitions
from app.features.taxonomy.service import TaxonomyService


def compose_suggestion_service(
    repository: SuggestionRepository,
    documents: PromotionPort,
    taxonomy: TaxonomyService,
    events: EventLogService,
) -> SuggestionService:
    """Build the suggestion service the way the app's dependency provider does."""
    handlers = build_dispatch(HandlerDeps(documents, taxonomy, repository))
    transitions = SuggestionTransitions(repository, handlers, events)
    return SuggestionService(repository, documents, handlers, transitions, events)
