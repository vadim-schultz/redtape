"""Maps an authenticated principal to the plain values the suggestion service takes."""

from __future__ import annotations

from app.features.auth.principal import Principal, UserPrincipal
from app.features.suggestions.service import SubmitterRef


def submitter_ref(principal: Principal) -> SubmitterRef:
    if isinstance(principal, UserPrincipal):
        return SubmitterRef("user", principal.user.id)
    return SubmitterRef("crawler", principal.api_key.id)


def submitter_display_name(principal: Principal) -> str | None:
    if isinstance(principal, UserPrincipal):
        return principal.user.display_name
    return principal.api_key.name
