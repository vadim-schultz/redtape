"""Dependency providers for the locations feature."""

from __future__ import annotations

from litestar.di import Provide
from sqlalchemy.orm import Session

from app.features.locations.repository import LocationsRepository
from app.features.locations.service import LocationsService


def provide_locations_repository(session: Session) -> LocationsRepository:
    """Bind a locations repository to the request session."""
    return LocationsRepository(session)


def provide_locations_service(
    locations_repository: LocationsRepository,
) -> LocationsService:
    """Bind the locations service to its repository."""
    return LocationsService(locations_repository)


router_dependencies = {
    "locations_repository": Provide(provide_locations_repository, sync_to_thread=False),
    "locations_service": Provide(
        provide_locations_service,
        sync_to_thread=False,
    ),
}
