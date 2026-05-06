"""Locale resolution middleware (`?locale=` → `Accept-Language` → de → en)."""

from __future__ import annotations

from litestar.connection import Request
from litestar.enums import ScopeType
from litestar.middleware.base import AbstractMiddleware

from app.locale_resolution import resolve_locale


class LocaleResolverMiddleware(AbstractMiddleware):
    """Resolve `request.state.locale` from `?locale=` then `Accept-Language`, else de → en."""

    scopes = {ScopeType.HTTP}

    async def __call__(self, scope, receive, send) -> None:  # type: ignore[no-untyped-def]
        if scope.get("state") is None:
            scope["state"] = {}
        request = Request(scope, receive)
        enabled: set[str] = getattr(request.app.state, "enabled_locale_codes", {"de", "en"})
        locale = resolve_locale(
            query_locale=request.query_params.get("locale"),
            accept_language=request.headers.get("accept-language"),
            enabled=enabled,
        )
        request.state["locale"] = locale
        await self.app(scope, receive, send)
