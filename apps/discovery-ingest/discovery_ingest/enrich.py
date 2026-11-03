"""Map FIM / LeiKa responses to discovery machine entity and claim bodies."""

from __future__ import annotations

from urllib.parse import urlparse
from uuid import UUID

from discovery_ingest.catalogue_export import CatalogueExportItem
from discovery_ingest.fim.keys import STECKBRIEF_PATH, steckbrief_key, steckbrief_url
from discovery_ingest.fim.models import FimDocument, Stammtext, Steckbrief
from discovery_ingest.schemas import CatalogueMachineRead, ClaimAppendRequest, EntityUpsertRequest


def _title_i18n_from_row(catalogue: CatalogueExportItem, document: FimDocument) -> dict[str, str]:
    if document.titel:
        return {"de": document.titel}
    if catalogue.title_i18n:
        return dict(catalogue.title_i18n)
    return {"de": "Leistung"}


def _official_url(catalogue: CatalogueExportItem, canonical_url: str) -> str:
    if catalogue.portal_url:
        return catalogue.portal_url
    return canonical_url


def _claims(
    catalogue: CatalogueExportItem,
    document: FimDocument,
    entity_id: UUID,
    canonical_url: str,
) -> list[ClaimAppendRequest]:
    """Build the optional ``metadata`` claim (real ``kurztext`` only) followed by the ``new_document`` claim."""
    claims: list[ClaimAppendRequest] = []
    if document.kurztext:
        claims.append(
            ClaimAppendRequest(discovery_entity_id=entity_id, kind="metadata", payload={"kurztext": document.kurztext})
        )
    claims.append(
        ClaimAppendRequest(
            discovery_entity_id=entity_id,
            kind="new_document",
            payload={
                "title_i18n": _title_i18n_from_row(catalogue, document),
                "official_url": _official_url(catalogue, canonical_url),
            },
        )
    )
    return claims


def fim_steckbrief_entity_request(
    catalogue: CatalogueExportItem,
    steckbrief: Steckbrief,
    *,
    fim_base_url: str,
) -> EntityUpsertRequest:
    """Build an entity upsert from a steckbrief.

    The label is the steckbrief's first non-blank of ``title``, ``titel`` and ``leistungsbezeichnung``;
    with none of them the label is ``None`` and the entity is still built.
    """
    canonical_url = steckbrief_url(fim_base_url, steckbrief.leistungsschluessel.strip())
    return EntityUpsertRequest(
        catalogue_service_id=catalogue.id,
        canonical_url=canonical_url,
        label=steckbrief.label(),
    )


def fim_steckbrief_claim_requests(
    catalogue: CatalogueExportItem,
    steckbrief: Steckbrief,
    *,
    entity_id: UUID,
    fim_base_url: str,
) -> list[ClaimAppendRequest]:
    """Build the ``metadata`` (only with a real ``kurztext``) and ``new_document`` claims from a steckbrief.

    The real steckbrief has no ``kurztext``, so it yields the ``new_document`` claim alone; no other field is
    substituted for the missing text.
    """
    canonical_url = fim_steckbrief_entity_request(catalogue, steckbrief, fim_base_url=fim_base_url).canonical_url
    return _claims(catalogue, steckbrief, entity_id, canonical_url)


def leika_stammtext_entity_request(
    catalogue: CatalogueExportItem,
    stammtext: Stammtext,
    *,
    fim_base_url: str,
) -> EntityUpsertRequest:
    """Build an entity upsert from a LeiKa stammtext."""
    canonical_url = (
        f"{fim_base_url.rstrip('/')}/api/v1/leistung-stammtexte/"
        f"{stammtext.redaktion_id.strip()}/{stammtext.leistung_id.strip()}/leika"
    )
    return EntityUpsertRequest(
        catalogue_service_id=catalogue.id,
        canonical_url=canonical_url,
        label=stammtext.titel,
    )


def leika_stammtext_claim_requests(
    catalogue: CatalogueExportItem,
    stammtext: Stammtext,
    *,
    entity_id: UUID,
    fim_base_url: str,
) -> list[ClaimAppendRequest]:
    """Build claims from LeiKa stammtext fields."""
    entity = leika_stammtext_entity_request(catalogue, stammtext, fim_base_url=fim_base_url)
    return _claims(catalogue, stammtext, entity_id, entity.canonical_url)


def catalogue_export_item_from_machine(read: CatalogueMachineRead) -> CatalogueExportItem:
    """Map a machine catalogue read DTO to offline export shape for enrich helpers."""
    return CatalogueExportItem(
        id=read.id,
        source=read.source,
        portal_url=read.portal_url,
        title_i18n=dict(read.title_i18n),
        raw_payload=dict(read.raw_payload),
    )


def fim_id_from_steckbrief_url(target_url: str) -> str | None:
    """Extract steckbrief key from a FIM Portal steckbrief URL."""
    path = urlparse(target_url).path
    marker = f"{STECKBRIEF_PATH}/"
    if marker not in path:
        return None
    suffix = path.split(marker, 1)[-1].strip("/")
    if not suffix or "/" in suffix:
        return None
    return suffix


def fim_id_from_catalogue(catalogue: CatalogueExportItem) -> str | None:
    """Resolve the steckbrief key from catalogue ``raw_payload`` exactly as the API fanout does."""
    return steckbrief_key(catalogue.raw_payload)


def leika_segments_from_catalogue(catalogue: CatalogueExportItem) -> tuple[str, str] | None:
    """Resolve LeiKa stammtext path segments from catalogue ``raw_payload``."""
    payload = catalogue.raw_payload
    redaktion = payload.get("redaktion_id")
    leistung = payload.get("leistung_id")
    if isinstance(leistung, str) and leistung.strip():
        leistung_id = leistung.strip()
    else:
        leika_key = payload.get("leika_key")
        if isinstance(leika_key, str) and leika_key.strip():
            leistung_id = leika_key.strip()
        else:
            return None
    if not isinstance(redaktion, str) or not redaktion.strip():
        return None
    return redaktion.strip(), leistung_id
