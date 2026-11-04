"""Maps an authenticated principal to the submitter that owns the suggestion rules."""

from __future__ import annotations

from app.features.auth.principal import Principal, UserPrincipal
from app.features.suggestions.submitters import CrawlerSubmitter, HumanSubmitter, Submitter


def submitter_for(principal: Principal) -> Submitter:
    """Return the human submitter for a signed-in user, otherwise the crawler submitter for the API key."""
    if isinstance(principal, UserPrincipal):
        return HumanSubmitter(principal.user.id)
    return CrawlerSubmitter(principal.api_key.id)


def submitter_display_name(principal: Principal) -> str | None:
    """Return the name shown for the submitter: the user's display name, or the API key's name."""
    if isinstance(principal, UserPrincipal):
        return principal.user.display_name
    return principal.api_key.name
