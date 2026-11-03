"""Dependency providers for the locales feature."""

from __future__ import annotations

from litestar.di import Provide
from sqlalchemy.orm import Session

from app.features.locales.repository import LocalesRepository
from app.features.locales.service import LocalesService


def provide_locales_repository(session: Session) -> LocalesRepository:
    """Build a `LocalesRepository` bound to the request session."""
    return LocalesRepository(session)


def provide_locales_service(locales_repository: LocalesRepository) -> LocalesService:
    """Build a `LocalesService` bound to the request's repository."""
    return LocalesService(locales_repository)


router_dependencies = {
    "locales_repository": Provide(provide_locales_repository, sync_to_thread=False),
    "locales_service": Provide(provide_locales_service, sync_to_thread=False),
}
