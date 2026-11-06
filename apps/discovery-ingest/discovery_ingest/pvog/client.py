"""PVOG Suchdienst HTTP client and catalogue row mapping."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import TypeVar
from urllib.parse import urlencode
from uuid import UUID

import httpx
from pydantic import BaseModel, JsonValue

from discovery_ingest.catalogue_scope import FEDERAL_ARS
from discovery_ingest.page_budget import PageBudget
from discovery_ingest.pvog.models import PvogBootstrap, PvogPage, PvogRecord, PvogSourcePath
from discovery_ingest.schemas import CatalogueBatchItem

BOOTSTRAP_PERSONAL_MATTER = "Geburt"
V7_PAGE_SIZE = 100
M = TypeVar("M", bound=BaseModel)


class PvogMappingError(ValueError):
    """Row cannot be mapped to a catalogue batch item."""


class PvogClientError(RuntimeError):
    """PVOG Suchdienst request failed."""


class PvogClient:
    """Fetch paginated Leistungen / servicedescription pages from PVOG Suchdienst."""

    def __init__(
        self,
        base_url: str,
        *,
        http_client: httpx.Client | None = None,
    ) -> None:
        """Keep the base URL and the optional HTTP client; without one each request opens its own."""
        self._base_url = base_url.rstrip("/")
        self._http_client = http_client

    def iter_records(
        self,
        *,
        ars: str = FEDERAL_ARS,
        max_pages: int | None = None,
    ) -> Iterator[tuple[str, PvogRecord]]:
        """Yield ``(personal_matter_code, record)`` from the v7 Lebenslagen tree walk and paginated search.

        ``max_pages`` caps every GET, the bootstrap page included.
        """
        budget = PageBudget(max_pages=max_pages)
        seen_lb_ids: set[str] = set()

        bootstrap_url = _build_v7_url(
            self._base_url,
            ars,
            personal_matter=BOOTSTRAP_PERSONAL_MATTER,
            facades=True,
        )
        if budget.exhausted:
            return
        bootstrap = self._fetch_page(bootstrap_url, PvogBootstrap)
        budget.spend_page()
        paths = bootstrap.leaf_paths()

        for code in bootstrap.leaf_codes():
            page_index = 0
            while True:
                if budget.exhausted:
                    return
                search_url = _build_v7_url(
                    self._base_url,
                    ars,
                    personal_matter=code,
                    facades=False,
                    page=page_index,
                )
                page = self._fetch_page(search_url, PvogPage)
                budget.spend_page()
                records, is_last = page.records_and_last
                for record in records:
                    lb_id = record.dedupe_id
                    if lb_id is None or lb_id in seen_lb_ids:
                        continue
                    seen_lb_ids.add(lb_id)
                    path = paths.get(code)
                    if path is not None:
                        record.attach_source_path(path)
                    yield code, record
                if is_last or not records:
                    break
                page_index += 1

    def fetch_personal_matter_vocabulary(self, *, ars: str = FEDERAL_ARS) -> list[str]:
        """Fetch the v7 facades bootstrap page and return its full leaf personalMatters vocabulary.

        Sorted ascending string order, deduplicated.
        """
        bootstrap_url = _build_v7_url(
            self._base_url,
            ars,
            personal_matter=BOOTSTRAP_PERSONAL_MATTER,
            facades=True,
        )
        return self._fetch_page(bootstrap_url, PvogBootstrap).leaf_codes()

    def _fetch_page(self, url: str, model: type[M]) -> M:
        """GET ``url`` and parse its JSON object as ``model``, wrapping transport, status and JSON failures in one error type."""
        try:
            response = self._get(url)
            response.raise_for_status()
            payload: JsonValue = response.json()
        except httpx.HTTPStatusError as err:
            raise PvogClientError(f"PVOG Suchdienst HTTP {err.response.status_code}") from err
        except httpx.HTTPError as err:
            raise PvogClientError(f"PVOG Suchdienst request failed: {type(err).__name__}: {err}") from err
        except ValueError as err:
            raise PvogClientError("PVOG Suchdienst returned invalid JSON") from err
        if not isinstance(payload, dict):
            raise PvogClientError("expected JSON object from PVOG Suchdienst")
        return model.model_validate(payload)

    def _get(self, url: str) -> httpx.Response:
        if self._http_client is not None:
            return self._http_client.get(url)
        with httpx.Client(trust_env=True, timeout=60.0) as client:
            return client.get(url)


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


@dataclass(frozen=True, slots=True)
class PvogStash:
    """The PVOG facts a catalogue row keeps beside its payload, and the served mapping version that stamps the path."""

    mapping_version: str
    personal_matter_code: str | None = None
    personal_matter_path: PvogSourcePath | None = None


def map_pvog_record(record: PvogRecord, *, jurisdiction_id: UUID, stash: PvogStash) -> CatalogueBatchItem:
    """Map one PVOG Suchdienst row to a machine batch item, keeping the PVOG facts of ``stash`` in its raw payload.

    Later harvest maps only complete PVOG evidence through the served crosswalk, so the path is stored beside the
    Lebenslage code it was captured with, and stamped with the mapping version the crosswalk was served under.
    """
    external_id = _external_id_for_record(record)
    title = record.title
    if title is None:
        raise PvogMappingError("row has no title (title, name, or leistungsname)")
    raw_payload: dict[str, object] = dict(record.raw)
    raw_payload.update(_stashed(record, stash))
    return CatalogueBatchItem(
        source="pvog",
        external_id=external_id,
        jurisdiction_id=jurisdiction_id,
        title_i18n={"de": title},
        description_i18n={"de": record.description} if record.description else None,
        portal_url=record.portal_url,
        raw_payload=raw_payload,
    )


def _stashed(record: PvogRecord, stash: PvogStash) -> dict[str, object]:
    """Return the reserved keys of a row's stored payload: the Lebenslage code and, when complete, its path and version."""
    stashed: dict[str, object] = {}
    if stash.personal_matter_code is not None:
        stashed["_personal_matter_code"] = stash.personal_matter_code
    source_path = stash.personal_matter_path or record.source_path
    if source_path is None:
        return stashed
    if stash.personal_matter_code is not None and source_path.leaf_code not in {None, stash.personal_matter_code}:
        raise PvogMappingError("personal matter code does not match its PVOG source path")
    stashed["_pvog_source_path"] = source_path.as_raw()
    stashed["_pvog_category_mapping_version"] = stash.mapping_version
    return stashed


def _external_id_for_record(record: PvogRecord) -> str:
    if record.leika_key is not None:
        return f"pvog:leika:{record.leika_key}"
    if record.lb_id:
        return f"pvog:lb:{record.lb_id}"
    raise PvogMappingError("row has no external id (leikakeys or id)")
