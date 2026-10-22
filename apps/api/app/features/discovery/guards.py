"""Route guards for discovery admin and machine APIs."""

from __future__ import annotations

from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException, PermissionDeniedException, ServiceUnavailableException
from litestar.handlers.base import BaseRouteHandler

from app.config import settings
from app.features.auth.guard_session import read_guard_user
from app.features.auth.guards import require_machine


def require_discovery_enabled(_: ASGIConnection, __: BaseRouteHandler) -> None:
    """Answer 503 while discovery is switched off."""

    if not settings.discovery_enabled:
        raise ServiceUnavailableException("Discovery is disabled")


def require_auth_enabled(_: ASGIConnection, __: BaseRouteHandler) -> None:
    """Answer 401 while JWT authentication is not configured."""

    if not settings.auth_enabled:
        raise NotAuthorizedException("Not authenticated")


def require_discovery_machine(connection: ASGIConnection, handler: BaseRouteHandler) -> None:
    """Allow machine API keys when discovery is enabled."""

    require_discovery_enabled(connection, handler)
    require_machine(connection, handler)


def require_discovery_admin_allowlist(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """Allow only JWT users whose email is on the discovery admin allowlist."""

    email = read_guard_user(connection, lambda user: user.email.lower())
    if email not in settings.discovery_admin_email_set:
        raise PermissionDeniedException("Discovery admin required")


DISCOVERY_ADMIN_GUARDS = [require_discovery_enabled, require_auth_enabled, require_discovery_admin_allowlist]
