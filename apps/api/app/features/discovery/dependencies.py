"""Dependency providers for the discovery feature."""

from __future__ import annotations

from litestar.di import Provide
from sqlalchemy.orm import Session

from app.features.auth.dependencies import router_dependencies as auth_dependencies
from app.features.discovery.repository import DiscoveryRepository
from app.features.discovery.service import DiscoveryAdminService


def provide_discovery_repository(session: Session) -> DiscoveryRepository:
    return DiscoveryRepository(session)


def provide_discovery_admin_service(discovery_repository: DiscoveryRepository) -> DiscoveryAdminService:
    return DiscoveryAdminService(discovery_repository)


router_dependencies = {
    **auth_dependencies,
    "discovery_repository": Provide(provide_discovery_repository, sync_to_thread=False),
    "discovery_admin_service": Provide(provide_discovery_admin_service, sync_to_thread=False),
}
