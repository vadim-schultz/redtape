"""Map FIM / LeiKa responses to discovery machine entity and claim bodies."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from discovery_ingest.catalogue_export import CatalogueExportItem
from discovery_ingest.fim.keys import STECKBRIEF_PATH, steckbrief_key, steckbrief_url
from discovery_ingest.schemas import CatalogueMachineRead, ClaimAppendRequest, EntityUpsertRequest

STECKBRIEF_LABEL_FIELDS = ("title", "titel", "leistungsbezeichnung")
"""Steckbrief fields tried for the entity label, in order.

The real response (probed 2026-10-26, decision D25) carries ``title`` and ``leistungsbezeichnung`` and no ``titel``;
``titel`` is the legacy shape of the early fixtures and is kept so older payloads still yield a label.
"""


def _first_text(payload: dict[str, Any], fields: tuple[str, ...]) -> str | None:
    """Return the first non-blank string among ``fields`` of ``payload``, stripped, or ``None``."""
    for field in fields:
        value = payload.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _title_i18n_from_row(catalogue: CatalogueExportItem, response: dict[str, Any]) -> dict[str, str]:
    titel = _first_text(response, ("titel",))
    if titel:
        return {"de": titel}
    if catalogue.title_i18n:
        return dict(catalogue.title_i18n)
    return {"de": "Leistung"}


def _official_url(catalogue: CatalogueExportItem, canonical_url: str) -> str:
    if catalogue.portal_url:
        return catalogue.portal_url
    return canonical_url


def _claims(
    catalogue: CatalogueExportItem,
    response: dict[str, Any],
    entity_id: UUID,
    canonical_url: str,
) -> list[ClaimAppendRequest]:
    """Build the optional ``metadata`` claim (real ``kurztext`` only) followed by the ``new_document`` claim."""
    claims: list[ClaimAppendRequest] = []
    kurztext = _first_text(response, ("kurztext",))
    if kurztext:
        claims.append(
            ClaimAppendRequest(discovery_entity_id=entity_id, kind="metadata", payload={"kurztext": kurztext})
        )
    claims.append(
        ClaimAppendRequest(
            discovery_entity_id=entity_id,
            kind="new_document",
            payload={
                "title_i18n": _title_i18n_from_row(catalogue, response),
                "official_url": _official_url(catalogue, canonical_url),
            },
        )
    )
    return claims


def fim_steckbrief_entity_request(
    catalogue: CatalogueExportItem,
    steckbrief: dict[str, Any],
    *,
    fim_base_url: str,
) -> EntityUpsertRequest:
    """Build an entity upsert from a steckbrief response.

    The label is the first non-blank of ``title``, ``titel`` and ``leistungsbezeichnung``
    (``STECKBRIEF_LABEL_FIELDS``); with none of them the label is ``None`` and the entity is still built.
    """
    key = steckbrief.get("leistungsschluessel")
    if not isinstance(key, str) or not key.strip():
        raise ValueError("steckbrief missing leistungsschluessel")
    canonical_url = steckbrief_url(fim_base_url, key.strip())
    return EntityUpsertRequest(
        catalogue_service_id=catalogue.id,
        canonical_url=canonical_url,
        label=_first_text(steckbrief, STECKBRIEF_LABEL_FIELDS),
    )


def fim_steckbrief_claim_requests(
    catalogue: CatalogueExportItem,
    steckbrief: dict[str, Any],
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
    return EntityUpsertRequest(
        catalogue_service_id=catalogue.id,
        canonical_url=canonical_url,
        label=_first_text(stammtext, ("titel",)),
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
