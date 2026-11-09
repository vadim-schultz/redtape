"""Read-only HTTP endpoint for the canonical category tree."""

from __future__ import annotations

from litestar import Controller, get

from app.features.taxonomy.service import TaxonomyService
from app.schema.taxonomy.read import CategoryNodeRead
from app.shared.locale import ResolvedLocale


class TaxonomyController(Controller):
    """Read the active canonical category tree."""

    path = "/"

    @get("/categories", sync_to_thread=True)
    def list_categories(self, taxonomy_service: TaxonomyService, locale: ResolvedLocale) -> list[CategoryNodeRead]:
        """Return the active category tree in the requested locale."""
        return taxonomy_service.list_categories(locale=locale)
