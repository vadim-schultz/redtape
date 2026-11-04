"""The authenticated caller of a request: a signed-in user or a machine API key."""

from __future__ import annotations

from dataclasses import dataclass

from app.models import AppUser
from app.models.api_key import ApiKey


@dataclass(frozen=True)
class UserPrincipal:
    """A caller authenticated with a Supabase user session."""

    user: AppUser

    @property
    def kind(self) -> str:
        """Return the discriminator `user` that tells the principal kinds apart."""
        return "user"

    @property
    def id(self) -> str:
        """Return the user id as text, for logs and audit fields."""
        return str(self.user.id)


@dataclass(frozen=True)
class MachinePrincipal:
    """A caller authenticated with an API key, typically a crawler."""

    api_key: ApiKey

    @property
    def kind(self) -> str:
        """Return the discriminator `crawler` that tells the principal kinds apart."""
        return "crawler"

    @property
    def id(self) -> str:
        """Return the API-key id as text, for logs and audit fields."""
        return str(self.api_key.id)


Principal = UserPrincipal | MachinePrincipal
