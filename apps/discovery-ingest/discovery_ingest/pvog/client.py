"""PVOG Suchdienst HTTP client and catalogue row mapping."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import httpx

from discovery_ingest.schemas import CatalogueBatchItem

FEDERAL_ARS = "000000000000"
BOOTSTRAP_PERSONAL_MATTER = "Geburt"
V7_PAGE_SIZE = 100


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

    def iter_records(
        self,
        *,
        ars: str = FEDERAL_ARS,
        max_pages: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Yield rows from v7 Lebenslagen tree walk and paginated search."""
        pages_fetched = 0
        seen_lb_ids: set[str] = set()

        bootstrap_url = _build_v7_url(
            self._base_url,
            ars,
            personal_matter=BOOTSTRAP_PERSONAL_MATTER,
            facades=True,
        )
        if not _budget_allows_fetch(max_pages, pages_fetched):
            return
        bootstrap = self._fetch_page(bootstrap_url)
        pages_fetched += 1

        for code in _personal_matter_codes_from_facades(bootstrap):
            page_index = 0
            while True:
                if not _budget_allows_fetch(max_pages, pages_fetched):
                    return
                search_url = _build_v7_url(
                    self._base_url,
                    ars,
                    personal_matter=code,
                    facades=False,
                    page=page_index,
                )
                payload = self._fetch_page(search_url)
                pages_fetched += 1
                records, is_last = _parse_v7_page(payload)
                for record in records:
                    lb_id = _lb_id_for_record(record)
                    if lb_id is None or lb_id in seen_lb_ids:
                        continue
                    seen_lb_ids.add(lb_id)
                    yield record
                if is_last or not records:
                    break
                page_index += 1

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


def _budget_allows_fetch(max_pages: int | None, pages_fetched: int) -> bool:
    if max_pages is None:
        return True
    return pages_fetched < max_pages


def _build_v7_url(
    base_url: str,
    ars: str,
    *,
    personal_matter: str,
    facades: bool,
    page: int | None = None,
) -> str:
    """Build a v7 servicedescriptions search URL with stable query parameter order."""
    params: list[tuple[str, str]] = [
        ("personalMatters", personal_matter),
        ("facades", "true" if facades else "false"),
        ("size", str(V7_PAGE_SIZE)),
    ]
    if page is not None:
        params.append(("page", str(page)))
    query = urlencode(params)
    return f"{base_url.rstrip('/')}/v7/servicedescriptions/{ars}?{query}"


def _personal_matter_codes_from_facades(payload: dict[str, Any]) -> list[str]:
    """Return sorted leaf ``personalMatters`` codes from a facades bootstrap payload."""
    facades = payload.get("facades")
    if not isinstance(facades, dict):
        return []
    matters = facades.get("personalMatters")
    if not isinstance(matters, list):
        return []
    codes: list[str] = []
    _collect_leaf_personal_matter_codes(matters, codes)
    return sorted(set(codes))


def _collect_leaf_personal_matter_codes(nodes: list[Any], out: list[str]) -> None:
    for node in nodes:
        if not isinstance(node, dict):
            continue
        children = node.get("children")
        if isinstance(children, list) and children:
            _collect_leaf_personal_matter_codes(children, out)
            continue
        code = node.get("code")
        if isinstance(code, str):
            stripped = code.strip()
            if stripped:
                out.append(stripped)


def _parse_v7_page(page: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    """Parse v7 ``serviceDescriptions`` pagination wrapper into rows and last-page flag."""
    wrapped = page.get("serviceDescriptions")
    if not isinstance(wrapped, dict):
        return [], True
    records = _dict_records(wrapped.get("content"))
    is_last = bool(wrapped.get("last", True))
    return records, is_last


def _dict_records(content: object) -> list[dict[str, Any]]:
    if not isinstance(content, list):
        return []
    records: list[dict[str, Any]] = []
    for entry in content:
        if isinstance(entry, dict):
            records.append(entry)
    return records


def _lb_id_for_record(record: dict[str, Any]) -> str | None:
    for key in ("id", "lbId"):
        value = record.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


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
