"""Enrich operations: one entity-and-claims sequence for FIM and LeiKa, with typed errors and no output."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, TypeVar
from uuid import UUID

from discovery_ingest.catalogue_export import CatalogueExportItem, load_catalogue_row
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.enrich import (
    fim_id_from_catalogue,
    fim_steckbrief_claim_requests,
    fim_steckbrief_entity_request,
    leika_segments_from_catalogue,
    leika_stammtext_claim_requests,
    leika_stammtext_entity_request,
)
from discovery_ingest.fim.client import FimClientError, SteckbriefSource
from discovery_ingest.fim.models import Stammtext, Steckbrief
from discovery_ingest.leika.client import LeikaClientError, StammtextSource
from discovery_ingest.operations.results import EnrichResult
from discovery_ingest.schemas import ClaimAppendRequest, EntityUpsertRequest

DocT = TypeVar("DocT")
DocInT = TypeVar("DocInT", contravariant=True)
LookupT = TypeVar("LookupT")


class EnrichError(Exception):
    """An enrich run could not start or fetch its document; the message is the operator text."""


class CatalogueRowNotFound(EnrichError):
    """The catalogue service id is not in the export."""


class MissingLookupKey(EnrichError):
    """The catalogue row carries no key the source can be asked for."""


class EnrichFetchError(EnrichError):
    """The source could not produce the document for the lookup key."""


class EntityMapping(Protocol[DocInT]):
    """Map one document to the entity upsert and the claims that follow it."""

    def entity_request(self, catalogue: CatalogueExportItem, document: DocInT) -> EntityUpsertRequest:
        """Return the entity upsert body for ``document``."""
        ...

    def claim_requests(
        self, catalogue: CatalogueExportItem, document: DocInT, entity_id: UUID
    ) -> list[ClaimAppendRequest]:
        """Return the claims to append to the entity ``entity_id``."""
        ...


class Enricher(EntityMapping[DocT], Protocol[LookupT, DocT]):
    """A source of one enrichment: find the lookup key, fetch the document, then map it."""

    name: str

    def lookup(self, catalogue: CatalogueExportItem) -> LookupT:
        """Return the key the source is asked for; raise :class:`MissingLookupKey` when the row has none."""
        ...

    def fetch(self, lookup: LookupT) -> DocT:
        """Return the document for ``lookup``; raise :class:`EnrichFetchError` when it cannot be fetched."""
        ...


class FimMapping:
    """Map a FIM steckbrief to the entity and claims, with links into ``fim_base_url``."""

    def __init__(self, fim_base_url: str) -> None:
        """Keep the FIM Portal base URL that the canonical links are built from."""
        self._fim_base_url = fim_base_url

    def entity_request(self, catalogue: CatalogueExportItem, document: Steckbrief) -> EntityUpsertRequest:
        """Return the steckbrief entity upsert."""
        return fim_steckbrief_entity_request(catalogue, document, fim_base_url=self._fim_base_url)

    def claim_requests(
        self, catalogue: CatalogueExportItem, document: Steckbrief, entity_id: UUID
    ) -> list[ClaimAppendRequest]:
        """Return the steckbrief claims for the entity ``entity_id``."""
        return fim_steckbrief_claim_requests(catalogue, document, entity_id=entity_id, fim_base_url=self._fim_base_url)


class LeikaMapping:
    """Map a LeiKa stammtext to the entity and claims, with links into ``fim_base_url``."""

    def __init__(self, fim_base_url: str) -> None:
        """Keep the FIM Portal base URL that the canonical links are built from."""
        self._fim_base_url = fim_base_url

    def entity_request(self, catalogue: CatalogueExportItem, document: Stammtext) -> EntityUpsertRequest:
        """Return the stammtext entity upsert."""
        return leika_stammtext_entity_request(catalogue, document, fim_base_url=self._fim_base_url)

    def claim_requests(
        self, catalogue: CatalogueExportItem, document: Stammtext, entity_id: UUID
    ) -> list[ClaimAppendRequest]:
        """Return the stammtext claims for the entity ``entity_id``."""
        return leika_stammtext_claim_requests(catalogue, document, entity_id=entity_id, fim_base_url=self._fim_base_url)


class FimEnricher:
    """Enrich from a FIM steckbrief keyed by the catalogue row's steckbrief key."""

    name = "fim"

    def __init__(self, source: SteckbriefSource, fim_base_url: str) -> None:
        """Keep the steckbrief source and the mapping base URL."""
        self._source = source
        self._mapping = FimMapping(fim_base_url)

    def lookup(self, catalogue: CatalogueExportItem) -> str:
        """Return the steckbrief key, or raise :class:`MissingLookupKey`."""
        key = fim_id_from_catalogue(catalogue)
        if key is None:
            raise MissingLookupKey(
                "catalogue row has no steckbrief key (fim_id, leistungsschluessel, leika_key or leikakeys)"
            )
        return key

    def fetch(self, lookup: str) -> Steckbrief:
        """Return the steckbrief for ``lookup``, or raise :class:`EnrichFetchError`."""
        try:
            return self._source.fetch_steckbrief(lookup)
        except FimClientError as err:
            raise EnrichFetchError(f"fim fetch failed: {err}") from err

    def entity_request(self, catalogue: CatalogueExportItem, document: Steckbrief) -> EntityUpsertRequest:
        """Return the steckbrief entity upsert."""
        return self._mapping.entity_request(catalogue, document)

    def claim_requests(
        self, catalogue: CatalogueExportItem, document: Steckbrief, entity_id: UUID
    ) -> list[ClaimAppendRequest]:
        """Return the steckbrief claims for the entity ``entity_id``."""
        return self._mapping.claim_requests(catalogue, document, entity_id)


class LeikaEnricher:
    """Enrich from a LeiKa stammtext keyed by the catalogue row's redaktion and leistung ids."""

    name = "leika"

    def __init__(self, source: StammtextSource, fim_base_url: str) -> None:
        """Keep the stammtext source and the mapping base URL."""
        self._source = source
        self._mapping = LeikaMapping(fim_base_url)

    def lookup(self, catalogue: CatalogueExportItem) -> tuple[str, str]:
        """Return the LeiKa path segments, or raise :class:`MissingLookupKey`."""
        segments = leika_segments_from_catalogue(catalogue)
        if segments is None:
            raise MissingLookupKey("catalogue row missing redaktion_id and leistung_id")
        return segments

    def fetch(self, lookup: tuple[str, str]) -> Stammtext:
        """Return the stammtext for the path segments, or raise :class:`EnrichFetchError`."""
        redaktion_id, leistung_id = lookup
        try:
            return self._source.fetch_stammtext(redaktion_id, leistung_id)
        except LeikaClientError as err:
            raise EnrichFetchError(f"leika fetch failed: {err}") from err

    def entity_request(self, catalogue: CatalogueExportItem, document: Stammtext) -> EntityUpsertRequest:
        """Return the stammtext entity upsert."""
        return self._mapping.entity_request(catalogue, document)

    def claim_requests(
        self, catalogue: CatalogueExportItem, document: Stammtext, entity_id: UUID
    ) -> list[ClaimAppendRequest]:
        """Return the stammtext claims for the entity ``entity_id``."""
        return self._mapping.claim_requests(catalogue, document, entity_id)


def catalogue_row(export_path: Path, catalogue_service_id: UUID) -> CatalogueExportItem:
    """Return the export row for ``catalogue_service_id``, or raise :class:`CatalogueRowNotFound`."""
    row = load_catalogue_row(export_path, catalogue_service_id)
    if row is None:
        raise CatalogueRowNotFound("catalogue service id not found in export")
    return row


def post_enrichment(
    mapping: EntityMapping[DocT],
    catalogue: CatalogueExportItem,
    document: DocT,
    client: DiscoveryIngestClient,
) -> EnrichResult:
    """Upsert the entity for ``document``, then append its claims in order.

    A refused request raises the machine API error; the entity stays posted when a claim is refused.
    """
    entity = client.catalogue.upsert_entity(mapping.entity_request(catalogue, document))
    claims = mapping.claim_requests(catalogue, document, entity.id)
    for claim in claims:
        client.catalogue.append_claim(claim)
    return EnrichResult(entity_id=entity.id, claims_posted=len(claims))


def run_enrich(
    enricher: Enricher[LookupT, DocT],
    catalogue: CatalogueExportItem,
    client: DiscoveryIngestClient,
) -> EnrichResult:
    """Look up, fetch and post one enrichment; the errors of each step propagate as :class:`EnrichError`."""
    lookup = enricher.lookup(catalogue)
    document = enricher.fetch(lookup)
    return post_enrichment(enricher, catalogue, document, client)
