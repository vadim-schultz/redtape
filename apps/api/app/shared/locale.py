"""Request locale and the set of enabled locale codes, resolved once per request."""

from __future__ import annotations

from dataclasses import dataclass

from litestar import Request

DEFAULT_LOCALE = "de"
FALLBACK_ORDER: tuple[str, ...] = ("de", "en")
DEFAULT_ENABLED_LOCALES: frozenset[str] = frozenset(FALLBACK_ORDER)


@dataclass(frozen=True, slots=True)
class ResolvedLocale:
    """The negotiated locale code plus the enabled codes available as fallbacks."""

    code: str
    enabled: set[str]


def provide_resolved_locale(request: Request) -> ResolvedLocale:
    """Read the middleware-resolved locale and the app's enabled locale codes."""
    state = request.scope.get("state") or {}
    enabled = getattr(request.app.state, "enabled_locale_codes", DEFAULT_ENABLED_LOCALES)
    return ResolvedLocale(code=str(state.get("locale", DEFAULT_LOCALE)), enabled=set(enabled))
