"""Facade the ingest commands and workers hold: ``client.<area>.<operation>(...)``."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

import httpx
from pydantic import SecretStr

from discovery_ingest.client.artifacts_api import ArtifactsAPI
from discovery_ingest.client.budget_api import BudgetAPI
from discovery_ingest.client.candidates_api import CandidatesAPI
from discovery_ingest.client.catalogue_api import CatalogueAPI
from discovery_ingest.client.embedding_api import EmbeddingsAPI
from discovery_ingest.client.http_client import MachineHttpClient
from discovery_ingest.client.runs_api import RunsAPI
from discovery_ingest.client.tasks_api import TasksAPI
from discovery_ingest.client.translation_api import TranslationsAPI

if TYPE_CHECKING:
    from discovery_ingest.config import IngestSettings


class DiscoveryIngestClient:
    """Reach every machine route through one shared connection, grouped by API area."""

    def __init__(self, base_url: str, api_key: SecretStr, *, transport: httpx.BaseTransport | None = None) -> None:
        """Wire the resource classes to one shared HTTP client; ``transport`` is the test seam."""
        self._http = MachineHttpClient(base_url, api_key, transport=transport)
        self.runs = RunsAPI(self._http)
        self.catalogue = CatalogueAPI(self._http)
        self.tasks = TasksAPI(self._http)
        self.candidates = CandidatesAPI(self._http)
        self.artifacts = ArtifactsAPI(self._http)
        self.budget = BudgetAPI(self._http)
        self.embeddings = EmbeddingsAPI(self._http)
        self.translations = TranslationsAPI(self._http)

    @classmethod
    def from_settings(cls, settings: IngestSettings) -> Self:
        """Build the client from the discovery URL and key in ``settings``."""
        return cls(settings.discovery_api_url, settings.discovery_api_key)

    def close(self) -> None:
        """Close the shared connection pool."""
        self._http.close()

    def __enter__(self) -> Self:
        """Return the client for a ``with`` block."""
        return self

    def __exit__(self, *_: object) -> None:
        """Close the connection pool when the block ends."""
        self.close()
