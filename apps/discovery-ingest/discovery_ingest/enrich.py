"""Map FIM / LeiKa responses to discovery machine entity and claim bodies."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from discovery_ingest.catalogue_export import CatalogueExportItem
from discovery_ingest.schemas import ClaimAppendRequest, EntityUpsertRequest


def _title_i18n_from_row(catalogue: CatalogueExportItem, response: dict[str, Any]) -> dict[str, str]:
    titel = response.get("titel")
    if isinstance(titel, str) and titel.strip():
        return {"de": titel.strip()}
    if catalogue.title_i18n:
        return dict(catalogue.title_i18n)
    return {"de": "Leistung"}


def _official_url(catalogue: CatalogueExportItem, canonical_url: str) -> str:
    if catalogue.portal_url:
        return catalogue.portal_url
    return canonical_url


def fim_steckbrief_entity_request(
    catalogue: CatalogueExportItem,
    steckbrief: dict[str, Any],
    *,
    fim_base_url: str,
) -> EntityUpsertRequest:
    """Build an entity upsert from a steckbrief response."""
    key = steckbrief.get("leistungsschluessel")
    if not isinstance(key, str) or not key.strip():
        raise ValueError("steckbrief missing leistungsschluessel")
    canonical_url = f"{fim_base_url.rstrip('/')}/api/v1/leistung-steckbriefe/{key.strip()}"
    titel = steckbrief.get("titel")
    label = titel.strip() if isinstance(titel, str) and titel.strip() else None
    return EntityUpsertRequest(
        catalogue_service_id=catalogue.id,
        canonical_url=canonical_url,
        label=label,
    )


def fim_steckbrief_claim_requests(
    catalogue: CatalogueExportItem,
    steckbrief: dict[str, Any],
    *,
    entity_id: UUID,
    fim_base_url: str,
) -> list[ClaimAppendRequest]:
    """Build metadata and new_document claims from steckbrief fields."""
    canonical_url = fim_steckbrief_entity_request(catalogue, steckbrief, fim_base_url=fim_base_url).canonical_url
    kurztext = steckbrief.get("kurztext")
    metadata_payload: dict[str, object] = {}
    if isinstance(kurztext, str) and kurztext.strip():
        metadata_payload["kurztext"] = kurztext.strip()
    claims: list[ClaimAppendRequest] = []
    if metadata_payload:
        claims.append(
            ClaimAppendRequest(
                discovery_entity_id=entity_id,
                kind="metadata",
                payload=metadata_payload,
            )
        )
    claims.append(
        ClaimAppendRequest(
            discovery_entity_id=entity_id,
            kind="new_document",
            payload={
                "title_i18n": _title_i18n_from_row(catalogue, steckbrief),
                "official_url": _official_url(catalogue, canonical_url),
            },
        )
    )
    return claims


def leika_stammtext_entity_request(
    catalogue: CatalogueExportItem,
    stammtext: dict[str, Any],
    *,
    fim_base_url: str,
) -> EntityUpsertRequest:
    """Build an entity upsert from a LeiKa stammtext response."""
    redaktion_id = stammtext.get("redaktion_id")
    leistung_id = stammtext.get("leistung_id")
    if not isinstance(redaktion_id, str) or not redaktion_id.strip():
        raise ValueError("stammtext missing redaktion_id")
    if not isinstance(leistung_id, str) or not leistung_id.strip():
        raise ValueError("stammtext missing leistung_id")
    canonical_url = (
        f"{fim_base_url.rstrip('/')}/api/v1/leistung-stammtexte/{redaktion_id.strip()}/{leistung_id.strip()}/leika"
    )
    titel = stammtext.get("titel")
    label = titel.strip() if isinstance(titel, str) and titel.strip() else None
    return EntityUpsertRequest(
        catalogue_service_id=catalogue.id,
        canonical_url=canonical_url,
        label=label,
    )


def leika_stammtext_claim_requests(
    catalogue: CatalogueExportItem,
    stammtext: dict[str, Any],
    *,
    entity_id: UUID,
    fim_base_url: str,
) -> list[ClaimAppendRequest]:
    """Build claims from LeiKa stammtext fields."""
    entity = leika_stammtext_entity_request(catalogue, stammtext, fim_base_url=fim_base_url)
    kurztext = stammtext.get("kurztext")
    metadata_payload: dict[str, object] = {}
    if isinstance(kurztext, str) and kurztext.strip():
        metadata_payload["kurztext"] = kurztext.strip()
    claims: list[ClaimAppendRequest] = []
    if metadata_payload:
        claims.append(
            ClaimAppendRequest(
                discovery_entity_id=entity_id,
                kind="metadata",
                payload=metadata_payload,
            )
        )
    claims.append(
        ClaimAppendRequest(
            discovery_entity_id=entity_id,
            kind="new_document",
            payload={
                "title_i18n": _title_i18n_from_row(catalogue, stammtext),
                "official_url": _official_url(catalogue, entity.canonical_url),
            },
        )
    )
    return claims


def fim_id_from_catalogue(catalogue: CatalogueExportItem) -> str | None:
    """Resolve steckbrief key from catalogue ``raw_payload``."""
    payload = catalogue.raw_payload
    for key in ("fim_id", "leistungsschluessel"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


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
