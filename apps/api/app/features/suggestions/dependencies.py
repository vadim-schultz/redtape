"""Dependency providers for the suggestions feature."""

from __future__ import annotations

from litestar.di import Provide
from sqlalchemy.orm import Session

from app.features.auth.dependencies import router_dependencies as auth_dependencies
from app.features.documents.dependencies import router_dependencies as document_dependencies
from app.features.documents.service import DocumentService
from app.features.events.dependencies import router_dependencies as event_dependencies
from app.features.suggestions.repository import SuggestionRepository
from app.features.suggestions.service import SuggestionService
from app.features.taxonomy.service import TaxonomyService


def provide_suggestion_repository(session: Session) -> SuggestionRepository:
    return SuggestionRepository(session)


def provide_suggestion_service(
    suggestion_repository: SuggestionRepository,
    document_service: DocumentService,
    taxonomy_service: TaxonomyService,
) -> SuggestionService:
    return SuggestionService(suggestion_repository, document_service, taxonomy_service)


router_dependencies = {
    **document_dependencies,
    **auth_dependencies,
    **event_dependencies,
    "suggestion_repository": Provide(provide_suggestion_repository, sync_to_thread=False),
    "suggestion_service": Provide(provide_suggestion_service, sync_to_thread=False),
}
