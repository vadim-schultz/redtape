"""Dependency providers for the discovery feature."""

from __future__ import annotations

from litestar.di import Provide
from sqlalchemy.orm import Session

from app.features.auth.dependencies import provide_machine_principal
from app.features.auth.dependencies import router_dependencies as auth_dependencies
from app.features.discovery.emit import DiscoveryEmitService
from app.features.discovery.repository import DiscoveryRepository
from app.features.discovery.service import DiscoveryAdminService, DiscoveryMachineService
from app.features.documents.dependencies import router_dependencies as document_dependencies
from app.features.events.dependencies import router_dependencies as event_dependencies
from app.features.suggestions.dependencies import (
    provide_suggestion_repository,
    provide_suggestion_service,
)
from app.features.suggestions.service import SuggestionService


def provide_discovery_repository(session: Session) -> DiscoveryRepository:
    return DiscoveryRepository(session)


def provide_discovery_admin_service(discovery_repository: DiscoveryRepository) -> DiscoveryAdminService:
    return DiscoveryAdminService(discovery_repository)


def provide_discovery_machine_service(discovery_repository: DiscoveryRepository) -> DiscoveryMachineService:
    return DiscoveryMachineService(discovery_repository)


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
    "discovery_emit_service": Provide(provide_discovery_emit_service, sync_to_thread=False),
    "suggestion_repository": Provide(provide_suggestion_repository, sync_to_thread=False),
    "suggestion_service": Provide(provide_suggestion_service, sync_to_thread=False),
    "machine_principal": Provide(provide_machine_principal, sync_to_thread=False),
}
