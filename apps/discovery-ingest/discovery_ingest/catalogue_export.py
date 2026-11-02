"""Load admin-style catalogue export fixtures for enrich CLIs."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, Field

from discovery_ingest.schemas import DiscoverySource


class CatalogueExportItem(BaseModel):
    """One catalogue row from an offline admin export."""

    id: UUID
    source: DiscoverySource
    portal_url: str | None = Field(default=None, max_length=500)
    title_i18n: dict[str, str] = Field(default_factory=dict)
    raw_payload: dict[str, object] = Field(default_factory=dict)


class CatalogueExport(BaseModel):
    """Paginated catalogue export snapshot."""

    items: list[CatalogueExportItem]


def load_catalogue_row(export_path: Path, catalogue_service_id: UUID) -> CatalogueExportItem | None:
    """Return the catalogue row matching ``catalogue_service_id`` or ``None``."""
    data = json.loads(export_path.read_text(encoding="utf-8"))
    export = CatalogueExport.model_validate(data)
    for item in export.items:
        if item.id == catalogue_service_id:
            return item
    return None
