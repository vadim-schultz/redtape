from __future__ import annotations

import uuid

from app.features.auth.jwt import TokenClaims
from app.features.auth.repository import UserRepository
from app.models import AppUser


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self._repo = repository

    def resolve(self, claims: TokenClaims) -> AppUser:
        return self._repo.upsert(
            id=uuid.UUID(claims.sub),
            email=claims.email.lower(),
            display_name=claims.display_name,
        )
