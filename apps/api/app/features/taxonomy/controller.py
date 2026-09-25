from __future__ import annotations

from litestar import Controller, Request, get

from app.features.taxonomy.service import TaxonomyService
from app.schema.taxonomy.read import TermRead


def _locale_context(request: Request) -> tuple[str, set[str]]:
    state = request.scope.get("state") or {}
    enabled: set[str] = getattr(request.app.state, "enabled_locale_codes", {"de", "en"})
    return str(state.get("locale", "de")), enabled


class TaxonomyController(Controller):
    """Read-only matrix axes: domains and life situations."""

    path = "/"

    @get("/domains", sync_to_thread=True)
    def list_domains(self, request: Request, taxonomy_service: TaxonomyService) -> list[TermRead]:
        locale, enabled = _locale_context(request)
        return taxonomy_service.list_domains(locale=locale, enabled_locales=enabled)

    @get("/life-situations", sync_to_thread=True)
    def list_life_situations(self, request: Request, taxonomy_service: TaxonomyService) -> list[TermRead]:
        locale, enabled = _locale_context(request)
        return taxonomy_service.list_situations(locale=locale, enabled_locales=enabled)
