"""GovData CKAN metadata and OZG Leistungen feed pagination."""

from __future__ import annotations

from collections.abc import Iterator
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx
from pydantic import JsonValue

from discovery_ingest.catalogue_scope import FEDERAL_ARS
from discovery_ingest.govdata.models import CkanPackage, CkanPackageShow, GovDataRow, OzgPage

LEISTUNGEN_RESOURCE_ID = "4b4fc7a2-8776-484d-834f-185590b181db"
DEFAULT_PAGE_SIZE = 100
OPEN_PVOG_PATH_SUFFIX = "/open-pvog"


class GovDataCkanError(RuntimeError):
    """GovData CKAN or Leistungen feed request failed."""


class GovDataCkanClient:
    """Resolve OZG Leistungen feed URL via CKAN and paginate rows."""

    def __init__(
        self,
        ckan_base_url: str,
        package_id: str,
        *,
        scope_ars: str | None = FEDERAL_ARS,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._ckan_base_url = ckan_base_url.rstrip("/")
        self._package_id = package_id
        self._scope_ars = scope_ars
        self._http_client = http_client

    def iter_record_pages(
        self,
        *,
        max_pages: int,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_records: int | None = None,
    ) -> Iterator[list[GovDataRow]]:
        """Yield each page of Leistungen rows (empty list ends pagination)."""
        if max_pages < 1:
            return
        feed_template = self._leistungen_feed_template_url()
        total_records = 0
        for page_index in range(max_pages):
            page_url = _page_url(feed_template, page=page_index, size=page_size)
            records = OzgPage.model_validate(self._fetch_json(page_url)).content
            if not records:
                break
            if max_records is not None:
                remaining = max_records - total_records
                if remaining <= 0:
                    break
                if len(records) > remaining:
                    records = records[:remaining]
            total_records += len(records)
            yield records
            if max_records is not None and total_records >= max_records:
                break
            if len(records) < page_size:
                break

    def _leistungen_feed_template_url(self) -> str:
        package = self._fetch_package_show()
        template = _leistungen_url_from_package(package)
        if self._scope_ars:
            return _scope_open_pvog_url(template, self._scope_ars)
        return template

    def _fetch_package_show(self) -> CkanPackage:
        url = f"{self._ckan_base_url}/package_show?id={self._package_id}"
        show = CkanPackageShow.model_validate(self._fetch_json(url))
        if show.result is None:
            raise GovDataCkanError("CKAN package_show response missing result object")
        return show.result

    def _fetch_json(self, url: str) -> dict[str, JsonValue]:
        """GET ``url`` and return its JSON object, wrapping transport, status and JSON failures in one error type."""
        try:
            response = self._get(url)
            if response.status_code >= 400:
                raise GovDataCkanError(f"GovData HTTP {response.status_code} for {url}")
            payload: JsonValue = response.json()
        except httpx.HTTPError as err:
            raise GovDataCkanError(f"GovData request failed: {type(err).__name__}: {err}") from err
        except ValueError as err:
            raise GovDataCkanError(f"GovData returned invalid JSON from {url}") from err
        if not isinstance(payload, dict):
            raise GovDataCkanError(f"expected JSON object from {url}")
        return payload

    def _get(self, url: str) -> httpx.Response:
        if self._http_client is not None:
            return self._http_client.get(url)
        with httpx.Client(trust_env=True, timeout=120.0) as client:
            return client.get(url)


def _leistungen_url_from_package(package: CkanPackage) -> str:
    if package.resources is None:
        raise GovDataCkanError("CKAN package has no resources list")
    for resource in package.resources:
        is_leistungen = resource.id == LEISTUNGEN_RESOURCE_ID or bool(
            resource.name and resource.name.lower() == "leistungen"
        )
        if is_leistungen and resource.url:
            return resource.url
    raise GovDataCkanError("CKAN package has no Leistungen resource URL")


def _scope_open_pvog_url(template_url: str, ars: str) -> str:
    """Rewrite unscoped ``open-pvog`` feed URL to ``open-pvog/{ars}`` with narrow scope."""
    parsed = urlparse(template_url)
    path = parsed.path
    marker = OPEN_PVOG_PATH_SUFFIX
    if marker not in path:
        raise GovDataCkanError(f"Leistungen URL missing {marker} path: {template_url}")
    scoped_path = path if f"{marker}/" in path else path.replace(marker, f"{marker}/{ars}", 1)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["includeAbove"] = "false"
    query["includeBelow"] = "false"
    new_query = urlencode(query)
    return urlunparse(parsed._replace(path=scoped_path, query=new_query))


def _page_url(template_url: str, *, page: int, size: int) -> str:
    parsed = urlparse(template_url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["page"] = str(page)
    query["size"] = str(size)
    if "order" not in query:
        query["order"] = "asc"
    new_query = urlencode(query)
    return urlunparse(parsed._replace(query=new_query))
