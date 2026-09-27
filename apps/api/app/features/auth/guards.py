from __future__ import annotations

from litestar.connection import ASGIConnection
from litestar.exceptions import PermissionDeniedException
from litestar.handlers.base import BaseRouteHandler
from litestar.types import Guard

from app.db import SessionLocal
from app.features.auth.dependencies import (
    machine_principal_from_connection,
    provide_jwt_verifier,
    user_from_connection,
)
from app.features.auth.repository import ApiKeyRepository, UserRepository
from app.features.auth.service import ApiKeyService, UserService
from app.models.user import ROLE_RANK, UserRole


def _role_allows(user_role: UserRole, min_role: UserRole) -> bool:
    return ROLE_RANK[user_role] >= ROLE_RANK[min_role]


def require_role(min_role: UserRole) -> Guard:
    """Guard factory: only lets connections whose stored role outranks `min_role` through."""

    def guard(connection: ASGIConnection, _: BaseRouteHandler) -> None:
        with SessionLocal() as session:
            user = user_from_connection(connection, provide_jwt_verifier(), UserService(UserRepository(session)))
            role = user.role
            session.commit()
        if not _role_allows(role, min_role):
            raise PermissionDeniedException("Insufficient role")

    return guard


def require_machine(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """Guard: only lets machine (X-API-Key) callers through; a logged-in human has the wrong kind of credential."""

    if connection.headers.get("X-API-Key") is None and connection.headers.get("Authorization") is not None:
        raise PermissionDeniedException("Machine credentials required")
    with SessionLocal() as session:
        machine_principal_from_connection(connection, ApiKeyService(ApiKeyRepository(session)))
        session.commit()
