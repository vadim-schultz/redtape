from __future__ import annotations

import logging

from litestar import Request
from litestar.connection import ASGIConnection
from litestar.di import Provide
from litestar.exceptions import NotAuthorizedException
from sqlalchemy.orm import Session

from app.config import settings
from app.features.auth.jwt import AuthError, JwtVerifier, jwks_key_resolver
from app.features.auth.repository import UserRepository
from app.features.auth.service import UserService
from app.models import AppUser

logger = logging.getLogger(__name__)

_jwt_verifier: JwtVerifier | None = None


def provide_user_repository(session: Session) -> UserRepository:
    return UserRepository(session)


def provide_user_service(user_repository: UserRepository) -> UserService:
    return UserService(user_repository)


def provide_jwt_verifier() -> JwtVerifier:
    global _jwt_verifier
    if _jwt_verifier is None:
        _jwt_verifier = JwtVerifier(
            key_resolver=jwks_key_resolver(settings.supabase_jwks_url or ""),
            issuer=settings.supabase_jwt_issuer or "",
            audience=settings.supabase_jwt_audience,
        )
    return _jwt_verifier


def _bearer_token(connection: ASGIConnection) -> str:
    header = connection.headers.get("Authorization")
    if header is None:
        raise AuthError("missing")
    scheme, _, token = header.partition(" ")
    if scheme != "Bearer" or not token or " " in token:
        raise AuthError("malformed")
    return token


def user_from_connection(connection: ASGIConnection, jwt_verifier: JwtVerifier, user_service: UserService) -> AppUser:
    """Resolve the database-backed user for a connection; shared by the dependency and by guards."""

    try:
        if not settings.auth_enabled:
            raise AuthError("auth_disabled")
        claims = jwt_verifier.verify(_bearer_token(connection))
    except AuthError as exc:
        logger.info("current_user rejected: %s", exc.reason)
        raise NotAuthorizedException("Not authenticated") from exc
    return user_service.resolve(claims)


def provide_current_user(request: Request, jwt_verifier: JwtVerifier, user_service: UserService) -> AppUser:
    return user_from_connection(request, jwt_verifier, user_service)


def provide_optional_user(request: Request, jwt_verifier: JwtVerifier, user_service: UserService) -> AppUser | None:
    if not settings.auth_enabled or request.headers.get("Authorization") is None:
        return None
    return user_from_connection(request, jwt_verifier, user_service)


router_dependencies = {
    "user_repository": Provide(provide_user_repository, sync_to_thread=False),
    "user_service": Provide(provide_user_service, sync_to_thread=False),
    "jwt_verifier": Provide(provide_jwt_verifier, sync_to_thread=False),
    "current_user": Provide(provide_current_user, sync_to_thread=False),
    "optional_user": Provide(provide_optional_user, sync_to_thread=False),
}
