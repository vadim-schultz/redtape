"""Dependency providers for the suggestions feature."""

from __future__ import annotations

from litestar.di import Provide
from sqlalchemy.orm import Session

from app.features.auth.dependencies import router_dependencies as auth_dependencies
from app.features.documents.dependencies import router_dependencies as document_dependencies
from app.features.documents.promotion import DocumentPromotion
from app.features.events.dependencies import router_dependencies as event_dependencies
from app.features.events.service import EventLogService
from app.features.suggestions.query import provide_suggestion_list_query
from app.features.suggestions.repository import SuggestionRepository
from app.features.suggestions.service import SuggestionService
from app.features.suggestions.submission import provide_submission
from app.features.taxonomy.service import TaxonomyService


def provide_suggestion_repository(session: Session) -> SuggestionRepository:
    return SuggestionRepository(session)


def provide_suggestion_service(
    suggestion_repository: SuggestionRepository,
    document_promotion: DocumentPromotion,
    taxonomy_service: TaxonomyService,
    event_log_service: EventLogService,
) -> SuggestionService:
    return SuggestionService(suggestion_repository, document_promotion, taxonomy_service, event_log_service)


router_dependencies = {
    **document_dependencies,
    **auth_dependencies,
    **event_dependencies,
    "suggestion_repository": Provide(provide_suggestion_repository, sync_to_thread=False),
    "suggestion_service": Provide(provide_suggestion_service, sync_to_thread=False),
    "submission": Provide(provide_submission, sync_to_thread=False),
    "suggestion_query": Provide(provide_suggestion_list_query, sync_to_thread=False),
}
