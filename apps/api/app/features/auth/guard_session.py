"""The one place guards open a database session; they read what they need before it closes."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import TypeVar

from litestar.connection import ASGIConnection
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.features.auth.dependencies import (
    machine_principal_from_connection,
    provide_jwt_verifier,
    user_from_connection,
)
from app.features.auth.repository import ApiKeyRepository, UserRepository
from app.features.auth.service import ApiKeyService, UserService
from app.models import AppUser

T = TypeVar("T")


@contextmanager
def guard_session() -> Iterator[Session]:
    """Yield a session, commit on success, always close."""

    with SessionLocal() as session:
        yield session
        session.commit()


def read_guard_user(connection: ASGIConnection, read: Callable[[AppUser], T]) -> T:
    """Resolve the connection's user and return `read(user)`, taken before the session closes."""

    with guard_session() as session:
        user = user_from_connection(connection, provide_jwt_verifier(), UserService(UserRepository(session)))
        return read(user)


def verify_guard_machine(connection: ASGIConnection) -> None:
    """Reject the connection unless it carries a valid machine API key."""

    with guard_session() as session:
        machine_principal_from_connection(connection, ApiKeyService(ApiKeyRepository(session)))
