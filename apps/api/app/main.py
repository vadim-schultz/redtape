from __future__ import annotations

from contextlib import asynccontextmanager

import anyio
from litestar import Litestar
from litestar.connection import Request
from litestar.di import Provide
from litestar.enums import ScopeType
from litestar.middleware.base import AbstractMiddleware, DefineMiddleware
from sqlalchemy import select

from app.db import SessionLocal, provide_session
from app.locale_resolution import resolve_locale
from app.models.locale import SupportedLocale
from app.routes import health, list_locales, translations_bundle


@asynccontextmanager
async def app_lifespan(app: Litestar):
    """Load enabled locale codes once at startup for middleware validation."""

    def load_enabled_locales() -> set[str]:
        try:
            with SessionLocal() as session:
                rows = session.scalars(
                    select(SupportedLocale.code).where(SupportedLocale.enabled.is_(True))
                ).all()
                return {str(code) for code in rows}
        except Exception:
            return set()

    enabled = await anyio.to_thread.run_sync(load_enabled_locales)
    app.state.enabled_locale_codes = enabled or {"de", "en"}
    yield


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


def create_app() -> Litestar:
    return Litestar(
        route_handlers=[health, list_locales, translations_bundle],
        dependencies={"session": Provide(provide_session)},
        middleware=[DefineMiddleware(LocaleResolverMiddleware)],
        lifespan=[app_lifespan],
    )


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
