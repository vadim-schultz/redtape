"""Dependency providers for the discovery feature."""

from __future__ import annotations

from litestar.di import Provide
from sqlalchemy.orm import Session

from app.features.auth.dependencies import provide_machine_principal
from app.features.auth.dependencies import router_dependencies as auth_dependencies
from app.features.discovery.repository import DiscoveryRepository
from app.features.discovery.service import DiscoveryAdminService, DiscoveryMachineService


def provide_discovery_repository(session: Session) -> DiscoveryRepository:
    return DiscoveryRepository(session)


def provide_discovery_admin_service(discovery_repository: DiscoveryRepository) -> DiscoveryAdminService:
    return DiscoveryAdminService(discovery_repository)


def provide_discovery_machine_service(discovery_repository: DiscoveryRepository) -> DiscoveryMachineService:
    return DiscoveryMachineService(discovery_repository)


router_dependencies = {
    **auth_dependencies,
    "discovery_repository": Provide(provide_discovery_repository, sync_to_thread=False),
    "discovery_admin_service": Provide(provide_discovery_admin_service, sync_to_thread=False),
    "discovery_machine_service": Provide(provide_discovery_machine_service, sync_to_thread=False),
    "machine_principal": Provide(provide_machine_principal, sync_to_thread=False),
}
