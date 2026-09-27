from __future__ import annotations

import uuid

from app.features.auth.jwt import TokenClaims
from app.features.auth.repository import UserRepository
from app.models import AppUser
from app.models.user import UserRole


class UnknownRoleError(ValueError):
    def __init__(self, role: str) -> None:
        valid = ", ".join(member.value for member in UserRole)
        super().__init__(f"unknown role {role!r}; valid roles: {valid}")


class UnknownUserError(ValueError):
    def __init__(self, email: str) -> None:
        super().__init__(f"no user with email {email!r}")


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self._repo = repository

    def resolve(self, claims: TokenClaims) -> AppUser:
        return self._repo.upsert(
            id=uuid.UUID(claims.sub),
            email=claims.email.lower(),
            display_name=claims.display_name,
        )

    def set_role(self, email: str, role: str) -> AppUser:
        try:
            parsed_role = UserRole(role)
        except ValueError:
            raise UnknownRoleError(role) from None
        user = self._repo.get_by_email(email)
        if user is None:
            raise UnknownUserError(email)
        user.role = parsed_role
        return user
