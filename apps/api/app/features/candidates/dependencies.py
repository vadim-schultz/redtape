"""Dependency providers for the public candidate view."""

from __future__ import annotations

from litestar.di import Provide
from sqlalchemy.orm import Session

from app.features.candidates.repository import PublicCandidateRepository
from app.features.candidates.screenshot_service import ScreenshotService
from app.features.candidates.service import CandidateReadService
from app.features.discovery.dependencies import (
    provide_discovery_budget_service,
    provide_discovery_repository,
    provide_metered_object_store,
)
from app.features.taxonomy.dependencies import router_dependencies as taxonomy_dependencies
from app.features.taxonomy.service import TaxonomyService
from app.shared.object_store.http import InjectedObjectStore


def provide_candidate_repository(session: Session) -> PublicCandidateRepository:
    return PublicCandidateRepository(session)


def provide_candidate_service(
    candidate_repository: PublicCandidateRepository, taxonomy_service: TaxonomyService
) -> CandidateReadService:
    return CandidateReadService(candidate_repository, taxonomy_service)


def provide_candidate_screenshot_service(
    candidate_repository: PublicCandidateRepository, object_store: InjectedObjectStore
) -> ScreenshotService:
    return ScreenshotService(candidate_repository, object_store)


router_dependencies = {
    **taxonomy_dependencies,
    "discovery_repository": Provide(provide_discovery_repository, sync_to_thread=False),
    "discovery_budget_service": Provide(provide_discovery_budget_service, sync_to_thread=False),
    "object_store": Provide(provide_metered_object_store, sync_to_thread=False),
    "candidate_repository": Provide(provide_candidate_repository, sync_to_thread=False),
    "candidate_service": Provide(provide_candidate_service, sync_to_thread=False),
    "candidate_screenshot_service": Provide(provide_candidate_screenshot_service, sync_to_thread=False),
}
