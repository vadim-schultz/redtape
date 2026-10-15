"""PVOG Suchdienst HTTP client and catalogue row mapping."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from uuid import UUID

import httpx

from discovery_ingest.schemas import CatalogueBatchItem

FEDERAL_ARS = "000000000000"


class PvogMappingError(ValueError):
    """Row cannot be mapped to a catalogue batch item."""


class PvogClient:
    """Fetch paginated Leistungen / servicedescription pages from PVOG Suchdienst."""

    def __init__(
        self,
        base_url: str,
        *,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._http_client = http_client

    def iter_records(self, *, ars: str = FEDERAL_ARS) -> Iterator[dict[str, Any]]:
        """Yield each row from paginated ``/v7/servicedescriptions/{ars}`` responses."""
        url: str | None = f"{self._base_url}/v7/servicedescriptions/{ars}"
        while url is not None:
            page = self._fetch_page(url)
            records = _content_records(page)
            if not records:
                break
            yield from records
            url = _next_page_url(page)

    def _fetch_page(self, url: str) -> dict[str, Any]:
        if self._http_client is not None:
            response = self._http_client.get(url)
        else:
            with httpx.Client(trust_env=True, timeout=60.0) as client:
                response = client.get(url)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("expected JSON object from PVOG Suchdienst")
        return payload


def map_pvog_record(
    row: dict[str, Any],
    *,
    jurisdiction_id: UUID,
) -> CatalogueBatchItem:
    """Map one PVOG Suchdienst row to a machine batch item."""
    external_id = _external_id_for_row(row)
    title = _title_for_row(row)
    description = _description_for_row(row)
    portal_url = _optional_str(row.get("url"))
    return CatalogueBatchItem(
        source="pvog",
        external_id=external_id,
        jurisdiction_id=jurisdiction_id,
        title_i18n={"de": title},
        description_i18n={"de": description} if description else None,
        portal_url=portal_url,
        raw_payload=dict(row),
    )


def _content_records(page: dict[str, Any]) -> list[dict[str, Any]]:
    content = page.get("content")
    if not isinstance(content, list):
        return []
    records: list[dict[str, Any]] = []
    for entry in content:
        if isinstance(entry, dict):
            records.append(entry)
    return records


def _next_page_url(page: dict[str, Any]) -> str | None:
    raw_next = page.get("next")
    if raw_next is None:
        return None
    if isinstance(raw_next, str):
        stripped = raw_next.strip()
        return stripped if stripped else None
    if isinstance(raw_next, dict):
        href = raw_next.get("href")
        if isinstance(href, str) and href.strip():
            return href.strip()
    return None


def _external_id_for_row(row: dict[str, Any]) -> str:
    portal_id = _optional_str(row.get("portalId")) or _optional_str(row.get("portal_id"))
    service_id = _optional_str(row.get("id")) or _optional_str(row.get("lbId"))
    if portal_id and service_id:
        return f"pvog:{portal_id}:{service_id}"
    raise PvogMappingError("row has no external id (portalId and id or lbId)")


def _title_for_row(row: dict[str, Any]) -> str:
    for key in ("title", "name", "leistungsname"):
        value = _optional_str(row.get(key))
        if value:
            return value
    raise PvogMappingError("row has no title (title, name, or leistungsname)")


def _description_for_row(row: dict[str, Any]) -> str | None:
    for key in ("description", "beschreibung"):
        value = _optional_str(row.get(key))
        if value:
            return value
    return None


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return str(value).strip() or None
