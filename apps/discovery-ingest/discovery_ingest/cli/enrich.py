"""The steps ``fim enrich`` and ``leika enrich`` share: read the catalogue row, then post the enrichment."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar
from uuid import UUID

import typer

from discovery_ingest.catalogue_export import CatalogueExportItem
from discovery_ingest.cli.context import api_client
from discovery_ingest.cli.errors import fail
from discovery_ingest.operations.enrich import CatalogueRowNotFound, Enricher, EnrichError, catalogue_row, run_enrich

LookupT = TypeVar("LookupT")
DocT = TypeVar("DocT")


def catalogue_or_fail(export: str, service_id: UUID) -> CatalogueExportItem:
    """Return the catalogue row of ``service_id`` in the export, or exit 1 with the reason."""
    try:
        return catalogue_row(Path(export), service_id)
    except CatalogueRowNotFound as err:
        fail(str(err))


def post_enrichment(ctx: typer.Context, enricher: Enricher[LookupT, DocT], catalogue: CatalogueExportItem) -> None:
    """Post one enrichment through the API client; exit 1 with the operator message on a known failure."""
    try:
        run_enrich(enricher, catalogue, api_client(ctx))
    except EnrichError as err:
        fail(str(err))
