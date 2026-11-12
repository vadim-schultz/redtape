"""HTTP handler of the translation admin coverage: allowlisted operators read the card coverage per locale."""

from __future__ import annotations

from litestar import Controller, get

from app.features.discovery.guards import DISCOVERY_ADMIN_GUARDS
from app.features.translation.admin_service import TranslationAdminService
from app.schema.translation.admin import TranslationCoverageResponse


class TranslationAdminController(Controller):
    """Read-only translation coverage for the discovery admin pages."""

    path = "/"
    guards = DISCOVERY_ADMIN_GUARDS

    @get("/coverage", sync_to_thread=True)
    def coverage(self, translation_admin_service: TranslationAdminService) -> TranslationCoverageResponse:
        """Count, per target locale, the card translations that are translated, stale, pending, claimed or failed."""
        return translation_admin_service.coverage()
