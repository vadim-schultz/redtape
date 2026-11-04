"""Persistence for application users and machine API keys; only hashes of keys are stored."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import ApiKey, AppUser


class UserRepository:
    """Persistence for application users, keyed by the Supabase user id."""

    def __init__(self, session: Session) -> None:
        """Bind the repository to the request's database session."""
        self._session = session

    def get(self, id: uuid.UUID) -> AppUser | None:
        """Return the user with this id, or `None` when none exists."""
        return self._session.get(AppUser, id)

    def get_by_email(self, email: str) -> AppUser | None:
        """Return the user whose email matches case-insensitively, or `None`."""
        return self._session.scalar(select(AppUser).where(func.lower(AppUser.email) == email.lower()))

    def upsert(self, *, id: uuid.UUID, email: str, display_name: str | None) -> AppUser:
        """Insert the user or update its email and display name, and stamp `last_seen_at`."""
        stmt = (
            insert(AppUser)
            .values(id=id, email=email, display_name=display_name, last_seen_at=func.now())
            .on_conflict_do_update(
                index_elements=[AppUser.id],
                set_={"email": email, "display_name": display_name, "last_seen_at": func.now()},
            )
            .returning(AppUser)
        )
        return self._session.scalars(stmt).one()


class ApiKeyRepository:
    """Persistence for machine API keys; the plaintext key is never stored."""

    def __init__(self, session: Session) -> None:
        """Bind the repository to the request's database session."""
        self._session = session

    def create(self, *, name: str, key_hash: str, key_prefix: str) -> ApiKey:
        """Insert a key record and flush it so its id is available to the caller."""
        record = ApiKey(id=uuid.uuid4(), name=name, key_hash=key_hash, key_prefix=key_prefix)
        self._session.add(record)
        self._session.flush()
        return record

    def get(self, id: uuid.UUID) -> ApiKey | None:
        """Return the API key with this id, or `None` when none exists."""
        return self._session.get(ApiKey, id)

    def get_by_hash(self, key_hash: str) -> ApiKey | None:
        """Return the API key with this hash, or `None` when none matches."""
        return self._session.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash))

    def get_by_prefix(self, key_prefix: str) -> ApiKey | None:
        """Return the API key with this public prefix, or `None` when none matches."""
        return self._session.scalar(select(ApiKey).where(ApiKey.key_prefix == key_prefix))

    def touch_last_used(self, api_key: ApiKey, when: datetime) -> None:
        """Record when the key was last used; flushes but does not commit."""
        api_key.last_used_at = when
        self._session.flush()
