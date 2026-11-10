"""Dependency providers for the public candidate view."""

from __future__ import annotations

from litestar.di import Provide
from sqlalchemy.orm import Session

from app.config import settings
from app.features.candidates.repository import PublicCandidateRepository
from app.features.candidates.screenshot_service import ScreenshotService
from app.features.candidates.search_plan import SearchPlanner
from app.features.candidates.service import CandidateReadService
from app.features.discovery.dependencies import (
    provide_discovery_budget_service,
    provide_discovery_repository,
    provide_metered_object_store,
)
from app.features.search.dependencies import InjectedQueryEmbedder, provide_query_embedder
from app.features.search.params import RetrievalParams
from app.features.taxonomy.dependencies import router_dependencies as taxonomy_dependencies
from app.features.taxonomy.service import TaxonomyService
from app.shared.object_store.http import InjectedObjectStore


def provide_candidate_repository(session: Session) -> PublicCandidateRepository:
    """Bind a public candidate repository to the request session."""
    return PublicCandidateRepository(session)


def provide_search_planner(query_embedder: InjectedQueryEmbedder) -> SearchPlanner:
    """Build the search planner over the shared query embedder and the current search settings."""
    return SearchPlanner(query_embedder, RetrievalParams.from_settings(settings), settings.search_hybrid_enabled)


def provide_candidate_service(
    candidate_repository: PublicCandidateRepository, taxonomy_service: TaxonomyService, search_planner: SearchPlanner
) -> CandidateReadService:
    """Bind the public candidate read service to its repository, the taxonomy service and the search planner."""
    return CandidateReadService(candidate_repository, taxonomy_service, search_planner)


def provide_candidate_screenshot_service(
    candidate_repository: PublicCandidateRepository, object_store: InjectedObjectStore
) -> ScreenshotService:
    """Bind the screenshot service to the candidate repository and the object store."""
    return ScreenshotService(candidate_repository, object_store)


router_dependencies = {
    **taxonomy_dependencies,
    "discovery_repository": Provide(provide_discovery_repository, sync_to_thread=False),
    "discovery_budget_service": Provide(provide_discovery_budget_service, sync_to_thread=False),
    "object_store": Provide(provide_metered_object_store, sync_to_thread=False),
    "query_embedder": Provide(provide_query_embedder, sync_to_thread=False),
    "search_planner": Provide(provide_search_planner, sync_to_thread=False),
    "candidate_repository": Provide(provide_candidate_repository, sync_to_thread=False),
    "candidate_service": Provide(provide_candidate_service, sync_to_thread=False),
    "candidate_screenshot_service": Provide(provide_candidate_screenshot_service, sync_to_thread=False),
}
