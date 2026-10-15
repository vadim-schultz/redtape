"""Parse OZG Leistungen JSON and map rows to catalogue batch items."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from discovery_ingest.schemas import CatalogueBatchItem

FEDERAL_ARS = "000000000000"


class GovDataMappingError(ValueError):
    """Row cannot be mapped to a catalogue batch item."""


class GovDataOzgClient:
    """Load OZG export pages from JSON files."""

    def __init__(self, records: list[dict[str, Any]]) -> None:
        self.records = records

    @classmethod
    def from_json_file(cls, path: Path) -> GovDataOzgClient:
        """Load a Leistungen JSON page from ``path``."""
        raw = json.loads(path.read_text(encoding="utf-8"))
        content = raw.get("content")
        if not isinstance(content, list):
            raise ValueError("expected top-level 'content' array in OZG JSON")
        records: list[dict[str, Any]] = []
        for entry in content:
            if isinstance(entry, dict):
                records.append(entry)
        return cls(records)


def map_govdata_record(
    row: dict[str, Any],
    *,
    federal_jurisdiction_id: UUID,
) -> CatalogueBatchItem:
    """Map one OZG Leistungen object to a machine batch item (public alias)."""
    return _map_govdata_record(row, federal_jurisdiction_id=federal_jurisdiction_id)


def _map_govdata_record(
    row: dict[str, Any],
    *,
    federal_jurisdiction_id: UUID,
) -> CatalogueBatchItem:
    """Map one OZG Leistungen object to a machine batch item."""
    external_id = _external_id_for_row(row)
    jurisdiction_id = _jurisdiction_id_for_row(row, federal_jurisdiction_id=federal_jurisdiction_id)
    title = _title_for_row(row)
    description = _description_for_row(row)
    portal_url = _optional_str(row.get("url"))
    return CatalogueBatchItem(
        source="govdata",
        external_id=external_id,
        jurisdiction_id=jurisdiction_id,
        title_i18n={"de": title},
        description_i18n={"de": description} if description else None,
        portal_url=portal_url,
        raw_payload=dict(row),
    )


def _external_id_for_row(row: dict[str, Any]) -> str:
    ozgid = _optional_str(row.get("ozgid"))
    if ozgid:
        return f"govdata:ozg:{ozgid}"
    leika_key = _optional_str(row.get("leika_key"))
    if leika_key:
        return f"govdata:leika:{leika_key}"
    stable_id = _optional_str(row.get("id"))
    if stable_id:
        return f"govdata:ozg:{stable_id}"
    raise GovDataMappingError("row has no external id (ozgid, leika_key, or id)")


def _jurisdiction_id_for_row(row: dict[str, Any], *, federal_jurisdiction_id: UUID) -> UUID:
    ars = _optional_str(row.get("ars"))
    if ars is None or ars == FEDERAL_ARS:
        return federal_jurisdiction_id
    raise GovDataMappingError(f"unsupported ars jurisdiction scope: {ars}")


def _title_for_row(row: dict[str, Any]) -> str:
    for key in ("leistungsname", "title", "name"):
        value = _optional_str(row.get(key))
        if value:
            return value
    raise GovDataMappingError("row has no title (leistungsname, title, or name)")


def _description_for_row(row: dict[str, Any]) -> str | None:
    for key in ("beschreibung", "description"):
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
