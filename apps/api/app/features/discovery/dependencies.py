"""Dependency providers for the discovery feature."""

from __future__ import annotations

from litestar.di import Provide
from sqlalchemy.orm import Session

from app.config import settings
from app.features.auth.dependencies import provide_machine_principal
from app.features.auth.dependencies import router_dependencies as auth_dependencies
from app.features.discovery.admin_service import DiscoveryAdminService
from app.features.discovery.artifact_read import ArtifactReadService
from app.features.discovery.artifact_upload import ArtifactUploadService
from app.features.discovery.budget_access import BudgetApiService
from app.features.discovery.budget_meter import ledger_meter
from app.features.discovery.budgets import BudgetService
from app.features.discovery.candidate_admin_service import CandidateAdminService
from app.features.discovery.candidate_emit import DiscoveryCandidateEmitService
from app.features.discovery.candidate_service import CandidateService
from app.features.discovery.catalogue_upsert import CatalogueUpsertService
from app.features.discovery.claim_ingest import ClaimIngest
from app.features.discovery.edge_service import EdgeService
from app.features.discovery.emit import DiscoveryEmitService
from app.features.discovery.repository import DiscoveryRepository
from app.features.discovery.run_service import DiscoveryRunService
from app.features.discovery.service import DiscoveryMachineService
from app.features.discovery.task_queue import TaskQueue
from app.features.documents.dependencies import router_dependencies as document_dependencies
from app.features.events.dependencies import router_dependencies as event_dependencies
from app.features.suggestions.dependencies import (
    provide_suggestion_repository,
    provide_suggestion_service,
)
from app.features.suggestions.service import SuggestionService
from app.features.taxonomy.service import TaxonomyService
from app.shared.object_store import ObjectStore
from app.shared.object_store.http import InjectedObjectStore
from app.shared.object_store.provider import get_object_store


def provide_discovery_repository(session: Session) -> DiscoveryRepository:
    return DiscoveryRepository(session)


def provide_discovery_admin_service(discovery_repository: DiscoveryRepository) -> DiscoveryAdminService:
    return DiscoveryAdminService(discovery_repository)


def provide_discovery_machine_service(discovery_repository: DiscoveryRepository) -> DiscoveryMachineService:
    return DiscoveryMachineService(
        discovery_repository,
        CatalogueUpsertService(discovery_repository),
        TaskQueue(discovery_repository),
        ClaimIngest(discovery_repository),
    )


def provide_discovery_candidate_service(
    discovery_repository: DiscoveryRepository, taxonomy_service: TaxonomyService
) -> CandidateService:
    return CandidateService(discovery_repository, taxonomy_service)


def provide_discovery_edge_service(discovery_repository: DiscoveryRepository) -> EdgeService:
    return EdgeService(discovery_repository)


def provide_discovery_candidate_admin_service(
    discovery_repository: DiscoveryRepository, taxonomy_service: TaxonomyService
) -> CandidateAdminService:
    return CandidateAdminService(discovery_repository, taxonomy_service)


def provide_discovery_candidate_emit_service(
    discovery_repository: DiscoveryRepository,
    suggestion_service: SuggestionService,
) -> DiscoveryCandidateEmitService:
    return DiscoveryCandidateEmitService(discovery_repository, suggestion_service)


def provide_discovery_artifact_upload_service(
    discovery_repository: DiscoveryRepository, object_store: InjectedObjectStore
) -> ArtifactUploadService:
    return ArtifactUploadService(discovery_repository, object_store, max_bytes=settings.object_store_max_bytes)


def provide_discovery_artifact_read_service(
    discovery_repository: DiscoveryRepository,
    object_store: InjectedObjectStore,
    discovery_budget_service: BudgetService,
) -> ArtifactReadService:
    return ArtifactReadService(
        discovery_repository,
        object_store,
        max_bytes=settings.object_store_max_bytes,
        presign_meter=ledger_meter(discovery_budget_service),
    )


def provide_discovery_budget_service(discovery_repository: DiscoveryRepository) -> BudgetService:
    return BudgetService(discovery_repository)


def provide_discovery_budget_api_service(
    discovery_repository: DiscoveryRepository, discovery_budget_service: BudgetService
) -> BudgetApiService:
    return BudgetApiService(discovery_repository, discovery_budget_service)


def provide_metered_object_store(discovery_budget_service: BudgetService) -> ObjectStore | None:
    """Override of the shared ``object_store`` dependency: every operation is counted in the budget ledger."""
    return get_object_store(ledger_meter(discovery_budget_service))


def provide_discovery_run_service(discovery_repository: DiscoveryRepository) -> DiscoveryRunService:
    return DiscoveryRunService(discovery_repository)


def provide_discovery_emit_service(
    discovery_repository: DiscoveryRepository,
    suggestion_service: SuggestionService,
) -> DiscoveryEmitService:
    return DiscoveryEmitService(discovery_repository, suggestion_service)


router_dependencies = {
    **auth_dependencies,
    **document_dependencies,
    **event_dependencies,
    "discovery_repository": Provide(provide_discovery_repository, sync_to_thread=False),
    "discovery_admin_service": Provide(provide_discovery_admin_service, sync_to_thread=False),
    "discovery_machine_service": Provide(provide_discovery_machine_service, sync_to_thread=False),
    "discovery_candidate_service": Provide(provide_discovery_candidate_service, sync_to_thread=False),
    "discovery_edge_service": Provide(provide_discovery_edge_service, sync_to_thread=False),
    "discovery_candidate_admin_service": Provide(provide_discovery_candidate_admin_service, sync_to_thread=False),
    "discovery_candidate_emit_service": Provide(provide_discovery_candidate_emit_service, sync_to_thread=False),
    "discovery_artifact_upload_service": Provide(provide_discovery_artifact_upload_service, sync_to_thread=False),
    "discovery_artifact_read_service": Provide(provide_discovery_artifact_read_service, sync_to_thread=False),
    "discovery_budget_service": Provide(provide_discovery_budget_service, sync_to_thread=False),
    "discovery_budget_api_service": Provide(provide_discovery_budget_api_service, sync_to_thread=False),
    "object_store": Provide(provide_metered_object_store, sync_to_thread=False),
    "discovery_run_service": Provide(provide_discovery_run_service, sync_to_thread=False),
    "discovery_emit_service": Provide(provide_discovery_emit_service, sync_to_thread=False),
    "suggestion_repository": Provide(provide_suggestion_repository, sync_to_thread=False),
    "suggestion_service": Provide(provide_suggestion_service, sync_to_thread=False),
    "machine_principal": Provide(provide_machine_principal, sync_to_thread=False),
}
