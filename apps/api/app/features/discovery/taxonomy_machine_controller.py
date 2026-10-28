"""Machine HTTP handler for the tag vocabulary."""

from __future__ import annotations

from litestar import Controller, get

from app.features.discovery.guards import require_discovery_machine
from app.features.taxonomy.service import TaxonomyService
from app.schema.taxonomy.read import VocabularyResponse


class DiscoveryTaxonomyMachineController(Controller):
    """Workers read the closed domain and life-situation vocabulary before they tag a page."""

    path = "/taxonomy"
    guards = [require_discovery_machine]

    @get("/", sync_to_thread=True)
    def vocabulary(self, taxonomy_service: TaxonomyService) -> VocabularyResponse:
        return taxonomy_service.vocabulary()
