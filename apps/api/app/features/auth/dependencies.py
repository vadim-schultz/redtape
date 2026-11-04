"""Dependency providers that resolve the user or machine principal of each request."""

from __future__ import annotations

import functools
import logging
import uuid

from litestar import Request
from litestar.connection import ASGIConnection
from litestar.di import Provide
from litestar.exceptions import ClientException, NotAuthorizedException
from sqlalchemy.orm import Session

from app.config import settings
from app.features.auth.jwt import AuthError, JwtVerifier, jwks_key_resolver
from app.features.auth.principal import MachinePrincipal, Principal, UserPrincipal
from app.features.auth.repository import ApiKeyRepository, UserRepository
from app.features.auth.service import ApiKeyError, ApiKeyService, UserService
from app.models import AppUser

logger = logging.getLogger(__name__)


def provide_user_repository(session: Session) -> UserRepository:
    """Build the user repository on the request's database session."""
    return UserRepository(session)


def provide_user_service(user_repository: UserRepository) -> UserService:
    """Build the user service on the request's user repository."""
    return UserService(user_repository)


def provide_api_key_repository(session: Session) -> ApiKeyRepository:
    """Build the API-key repository on the request's database session."""
    return ApiKeyRepository(session)


def provide_api_key_service(api_key_repository: ApiKeyRepository) -> ApiKeyService:
    """Build the API-key service on the request's API-key repository."""
    return ApiKeyService(api_key_repository)


@functools.lru_cache(maxsize=1)
def default_jwt_verifier() -> JwtVerifier:
    """Build the production verifier from settings once; tests replace it through this name."""
    return JwtVerifier(
        key_resolver=jwks_key_resolver(settings.supabase_jwks_url or ""),
        issuer=settings.supabase_jwt_issuer or "",
        audience=settings.supabase_jwt_audience,
    )


def provide_jwt_verifier() -> JwtVerifier:
    """Return the process-wide JWT verifier, built once from settings."""
    return default_jwt_verifier()


def _bearer_token(connection: ASGIConnection) -> str:
    header = connection.headers.get("Authorization")
    if header is None:
        raise AuthError("missing")
    scheme, _, token = header.partition(" ")
    if scheme != "Bearer" or not token or " " in token:
        raise AuthError("malformed")
    return token


_RESOLVED_USER_ID = "auth_user_id"
_RESOLVED_API_KEY_ID = "auth_api_key_id"


def _recall(connection: ASGIConnection, key: str) -> uuid.UUID | None:
    """Return the identity a guard already resolved on this request, as a plain id."""
    value = connection.state.get(key)
    return value if isinstance(value, uuid.UUID) else None


def user_from_connection(connection: ASGIConnection, jwt_verifier: JwtVerifier, user_service: UserService) -> AppUser:
    """Resolve the database-backed user for a connection; shared by the dependency and by guards.

    The first call on a request verifies the token and records the user id on the request; later calls on the
    same request load that row by primary key instead of verifying the token again.
    """
    recalled = _recall(connection, _RESOLVED_USER_ID)
    if recalled is not None and (user := user_service.get(recalled)) is not None:
        return user
    try:
        if not settings.auth_enabled:
            raise AuthError("auth_disabled")
        claims = jwt_verifier.verify(_bearer_token(connection))
    except AuthError as exc:
        logger.info("current_user rejected: %s", exc.reason)
        raise NotAuthorizedException("Not authenticated") from exc
    user = user_service.resolve(claims)
    connection.state[_RESOLVED_USER_ID] = user.id
    return user


def provide_current_user(request: Request, jwt_verifier: JwtVerifier, user_service: UserService) -> AppUser:
    """Return the signed-in user for this request; refuse with 401 when the token is missing or invalid."""
    return user_from_connection(request, jwt_verifier, user_service)


def _api_key_value(connection: ASGIConnection) -> str:
    header = connection.headers.get("X-API-Key")
    if header is None:
        raise AuthError("missing")
    return header


def machine_principal_from_connection(connection: ASGIConnection, api_key_service: ApiKeyService) -> MachinePrincipal:
    """Resolve the machine principal for a connection; shared by the dependency and by guards.

    Verifies the key once per request, then reuses the recorded key id like `user_from_connection` does.
    """
    recalled = _recall(connection, _RESOLVED_API_KEY_ID)
    if recalled is not None and (record := api_key_service.get(recalled)) is not None:
        return MachinePrincipal(api_key=record)
    try:
        record = api_key_service.verify(_api_key_value(connection))
    except (AuthError, ApiKeyError) as exc:
        logger.info("machine principal rejected: %s", exc)
        raise NotAuthorizedException("Not authenticated") from exc
    connection.state[_RESOLVED_API_KEY_ID] = record.id
    return MachinePrincipal(api_key=record)


def provide_machine_principal(request: Request, api_key_service: ApiKeyService) -> MachinePrincipal:
    """Return the API-key principal for this request; refuse with 401 when the key is missing or invalid."""
    return machine_principal_from_connection(request, api_key_service)


def provide_optional_user(request: Request, jwt_verifier: JwtVerifier, user_service: UserService) -> AppUser | None:
    """Return the signed-in user when auth is enabled and a bearer token is sent, otherwise `None`."""
    if not settings.auth_enabled or request.headers.get("Authorization") is None:
        return None
    return user_from_connection(request, jwt_verifier, user_service)


def provide_principal(
    request: Request, jwt_verifier: JwtVerifier, user_service: UserService, api_key_service: ApiKeyService
) -> Principal:
    """Accept either a bearer user or an API key; refuse to guess when both are present (D8)."""
    has_bearer = request.headers.get("Authorization") is not None
    has_api_key = request.headers.get("X-API-Key") is not None
    if has_bearer and has_api_key:
        raise ClientException("Ambiguous credentials")
    if has_bearer:
        return UserPrincipal(user=user_from_connection(request, jwt_verifier, user_service))
    return machine_principal_from_connection(request, api_key_service)


router_dependencies = {
    "user_repository": Provide(provide_user_repository, sync_to_thread=False),
    "user_service": Provide(provide_user_service, sync_to_thread=False),
    "api_key_repository": Provide(provide_api_key_repository, sync_to_thread=False),
    "api_key_service": Provide(provide_api_key_service, sync_to_thread=False),
    "jwt_verifier": Provide(provide_jwt_verifier, sync_to_thread=False),
    "current_user": Provide(provide_current_user, sync_to_thread=False),
    "optional_user": Provide(provide_optional_user, sync_to_thread=False),
    "principal": Provide(provide_principal, sync_to_thread=False),
}
