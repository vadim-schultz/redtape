"""Request locale and the set of enabled locale codes, resolved once per request."""

from __future__ import annotations

from dataclasses import dataclass

from litestar import Request

_DEFAULT_LOCALE = "de"
_DEFAULT_ENABLED = ("de", "en")


@dataclass(frozen=True, slots=True)
class ResolvedLocale:
    """The negotiated locale code plus the enabled codes available as fallbacks."""

    code: str
    enabled: set[str]


def provide_resolved_locale(request: Request) -> ResolvedLocale:
    """Read the middleware-resolved locale and the app's enabled locale codes."""
    state = request.scope.get("state") or {}
    enabled = getattr(request.app.state, "enabled_locale_codes", _DEFAULT_ENABLED)
    return ResolvedLocale(code=str(state.get("locale", _DEFAULT_LOCALE)), enabled=set(enabled))
