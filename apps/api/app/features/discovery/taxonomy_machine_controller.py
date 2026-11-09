"""Machine HTTP handler for the canonical category vocabulary."""

from __future__ import annotations

from litestar import Controller, get

from app.features.discovery.guards import require_discovery_machine
from app.features.taxonomy.service import TaxonomyService
from app.schema.taxonomy.read import VocabularyResponse


class DiscoveryTaxonomyMachineController(Controller):
    """Workers read the active canonical category vocabulary before they tag a page."""

    path = "/taxonomy"
    guards = [require_discovery_machine]

    @get("/", sync_to_thread=True)
    def vocabulary(self, taxonomy_service: TaxonomyService) -> VocabularyResponse:
        """Return active canonical categories and their source parent metadata."""
        return taxonomy_service.vocabulary()
