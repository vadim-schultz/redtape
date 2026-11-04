"""HTTP endpoint for the authenticated user's own profile."""

from __future__ import annotations

from litestar import Controller, get
from litestar.datastructures import CacheControlHeader

from app.models import AppUser
from app.schema.auth.read import UserRead


class MeController(Controller):
    """The authenticated user's own profile."""

    path = "/"

    @get("/me", sync_to_thread=True, cache_control=CacheControlHeader(no_store=True))
    def get_me(self, current_user: AppUser) -> UserRead:
        """Return the signed-in user's profile; the response is sent with `no-store`."""
        return UserRead.model_validate(current_user)
