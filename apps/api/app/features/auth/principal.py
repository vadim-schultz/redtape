from __future__ import annotations

from dataclasses import dataclass

from app.models import AppUser
from app.models.api_key import ApiKey


@dataclass(frozen=True)
class UserPrincipal:
    user: AppUser

    @property
    def kind(self) -> str:
        return "user"

    @property
    def id(self) -> str:
        return str(self.user.id)


@dataclass(frozen=True)
class MachinePrincipal:
    api_key: ApiKey

    @property
    def kind(self) -> str:
        return "crawler"

    @property
    def id(self) -> str:
        return str(self.api_key.id)


Principal = UserPrincipal | MachinePrincipal
