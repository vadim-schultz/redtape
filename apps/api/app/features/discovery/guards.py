"""Route guards for discovery admin and machine APIs."""

from __future__ import annotations

from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException, PermissionDeniedException, ServiceUnavailableException
from litestar.handlers.base import BaseRouteHandler

from app.config import settings
from app.db import SessionLocal
from app.features.auth.dependencies import provide_jwt_verifier, user_from_connection
from app.features.auth.guards import require_machine
from app.features.auth.repository import UserRepository
from app.features.auth.service import UserService


def require_discovery_machine(connection: ASGIConnection, handler: BaseRouteHandler) -> None:
    """Allow machine API keys when discovery is enabled."""

    if not settings.discovery_enabled:
        raise ServiceUnavailableException("Discovery is disabled")
    require_machine(connection, handler)


def require_discovery_admin(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """Allow only JWT users whose email is on the discovery admin allowlist."""

    if not settings.discovery_enabled:
        raise ServiceUnavailableException("Discovery is disabled")
    if not settings.auth_enabled:
        raise NotAuthorizedException("Not authenticated")
    with SessionLocal() as session:
        user = user_from_connection(connection, provide_jwt_verifier(), UserService(UserRepository(session)))
        email = user.email.lower()
        session.commit()
    if email not in settings.discovery_admin_email_set:
        raise PermissionDeniedException("Discovery admin required")
