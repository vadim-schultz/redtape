"""Litestar controller for `/locales` and `/translations`."""

from __future__ import annotations

from litestar import Controller, get

from app.features.locales.service import LocalesService
from app.schema.locale.read import LocaleRead, TranslationBundle
from app.shared.locale import ResolvedLocale

_TRANSLATIONS_CACHE_CONTROL = "public, max-age=3600, stale-while-revalidate=86400"


class LocalesController(Controller):
    """Enabled locales and their UI translation bundles."""

    path = "/"

    @get("/locales", sync_to_thread=True)
    def list_locales(self, locales_service: LocalesService) -> list[LocaleRead]:
        """Return every enabled locale."""
        return locales_service.list_enabled()

    @get("/translations", sync_to_thread=True, response_headers={"Cache-Control": _TRANSLATIONS_CACHE_CONTROL})
    def translations(self, locales_service: LocalesService, locale: ResolvedLocale) -> TranslationBundle:
        """Return the UI translation bundle for the request's resolved locale."""
        return locales_service.translations_for(locale.code)
