"""Application lifespan hooks (startup / shutdown)."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import anyio
from litestar import Litestar
from sqlalchemy import select

from app.db import SessionLocal
from app.models.locale import SupportedLocale
from app.shared.locale import DEFAULT_ENABLED_LOCALES

logger = logging.getLogger(__name__)

REFRESH_INTERVAL_SECONDS = 300.0
RETRY_INTERVAL_SECONDS = 30.0

_FALLBACK_LOCALES: frozenset[str] = DEFAULT_ENABLED_LOCALES


def _load_enabled_locales() -> set[str]:
    """Return the enabled locale codes; raise when the database cannot answer."""
    with SessionLocal() as session:
        rows = session.scalars(select(SupportedLocale.code).where(SupportedLocale.enabled.is_(True))).all()
        return {str(code) for code in rows}


async def _refresh(app: Litestar, *, startup: bool) -> bool:
    """Apply the next load outcome to `app.state` and report whether it now serves the fallback.

    A startup failure is loud (`ERROR`) because nothing has ever come from the database
    yet; a later refresh failure is quieter (`WARNING`) because the last good set keeps
    serving. An empty table is always a `WARNING`: disabling every locale is almost
    certainly a mistake. Only a changed set, or the end of the fallback, gets an `INFO`
    line, so a steady refresh stays silent.
    """
    previous = getattr(app.state, "enabled_locale_codes", _FALLBACK_LOCALES)
    on_fallback = previous is _FALLBACK_LOCALES

    try:
        enabled = await anyio.to_thread.run_sync(_load_enabled_locales)
    except Exception as exc:
        logger.log(
            logging.ERROR if on_fallback else logging.WARNING,
            "failed to load enabled locales: %s",
            exc,
            exc_info=True,
        )
        app.state.enabled_locale_codes = _FALLBACK_LOCALES if startup else previous
        return app.state.enabled_locale_codes is _FALLBACK_LOCALES

    if not enabled:
        logger.warning("the locale table has no enabled row; serving %s", sorted(previous))
        app.state.enabled_locale_codes = _FALLBACK_LOCALES if startup else previous
        return app.state.enabled_locale_codes is _FALLBACK_LOCALES

    if on_fallback and startup:
        logger.info("loaded enabled locales: %s", sorted(enabled))
    elif on_fallback:
        logger.info("the fallback is over; enabled locales are %s", sorted(enabled))
    elif previous != enabled:
        logger.info("enabled locales changed to %s", sorted(enabled))
    app.state.enabled_locale_codes = enabled
    return False


async def _refresh_forever(app: Litestar) -> None:
    """Keep the enabled locales fresh for as long as the app runs.

    Retries quickly while serving the fallback and backs off to the normal interval once
    a real set has been loaded, so recovery is fast but the steady state is cheap.
    """
    while True:
        on_fallback = await _refresh(app, startup=False)
        await anyio.sleep(RETRY_INTERVAL_SECONDS if on_fallback else REFRESH_INTERVAL_SECONDS)


@asynccontextmanager
async def app_lifespan(app: Litestar) -> AsyncIterator[None]:
    """Load the enabled locales at startup and keep them fresh while the app runs."""
    await _refresh(app, startup=True)
    async with anyio.create_task_group() as tasks:
        tasks.start_soon(_refresh_forever, app)
        yield
        tasks.cancel_scope.cancel()
