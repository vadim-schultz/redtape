from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import ApiKey, AppUser


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, id: uuid.UUID) -> AppUser | None:
        return self._session.get(AppUser, id)

    def get_by_email(self, email: str) -> AppUser | None:
        return self._session.scalar(select(AppUser).where(func.lower(AppUser.email) == email.lower()))

    def upsert(self, *, id: uuid.UUID, email: str, display_name: str | None) -> AppUser:
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
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, *, name: str, key_hash: str, key_prefix: str) -> ApiKey:
        record = ApiKey(id=uuid.uuid4(), name=name, key_hash=key_hash, key_prefix=key_prefix)
        self._session.add(record)
        self._session.flush()
        return record

    def get(self, id: uuid.UUID) -> ApiKey | None:
        return self._session.get(ApiKey, id)

    def get_by_hash(self, key_hash: str) -> ApiKey | None:
        return self._session.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash))

    def get_by_prefix(self, key_prefix: str) -> ApiKey | None:
        return self._session.scalar(select(ApiKey).where(ApiKey.key_prefix == key_prefix))

    def touch_last_used(self, api_key: ApiKey, when: datetime) -> None:
        api_key.last_used_at = when
        self._session.flush()
