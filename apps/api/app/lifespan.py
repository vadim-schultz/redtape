"""Application lifespan hooks (startup / shutdown)."""

from __future__ import annotations

from contextlib import asynccontextmanager

import anyio
from litestar import Litestar
from sqlalchemy import select

from app.db import SessionLocal
from app.models.locale import SupportedLocale


@asynccontextmanager
async def app_lifespan(app: Litestar):
    """Load enabled locale codes once at startup for locale middleware."""

    def load_enabled_locales() -> set[str]:
        try:
            with SessionLocal() as session:
                rows = session.scalars(select(SupportedLocale.code).where(SupportedLocale.enabled.is_(True))).all()
                return {str(code) for code in rows}
        except Exception:
            return set()

    enabled = await anyio.to_thread.run_sync(load_enabled_locales)
    app.state.enabled_locale_codes = enabled or {"de", "en"}
    yield
