from __future__ import annotations

import uuid

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import AppUser


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, id: uuid.UUID) -> AppUser | None:
        return self._session.get(AppUser, id)

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
