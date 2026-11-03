"""Parse OZG Leistungen JSON and map rows to catalogue batch items."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from pydantic import JsonValue

from discovery_ingest.catalogue_scope import FEDERAL_ARS
from discovery_ingest.govdata.models import GovDataRow, OzgPage
from discovery_ingest.schemas import CatalogueBatchItem


class GovDataMappingError(ValueError):
    """Row cannot be mapped to a catalogue batch item."""


class GovDataOzgClient:
    """Load OZG export pages from JSON files."""

    def __init__(self, records: list[GovDataRow]) -> None:
        """Keep the rows of one page."""
        self.records = records

    @classmethod
    def from_json_file(cls, path: Path) -> GovDataOzgClient:
        """Load a Leistungen JSON page from ``path``; the file must hold a top-level ``content`` array."""
        raw: JsonValue = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or not isinstance(raw.get("content"), list):
            raise ValueError("expected top-level 'content' array in OZG JSON")
        return cls(OzgPage.model_validate(raw).content)


def map_govdata_record(
    row: GovDataRow,
    *,
    federal_jurisdiction_id: UUID,
) -> CatalogueBatchItem:
    """Map one OZG Leistungen row to a machine batch item."""
    external_id = _external_id_for_row(row)
    jurisdiction_id = _jurisdiction_id_for_row(row, federal_jurisdiction_id=federal_jurisdiction_id)
    title = row.title
    if title is None:
        raise GovDataMappingError(
            "row has no title (leika_name, leistungsname, title, name, leika_bezeichnung, or ozg_bezeichnung)",
        )
    description = row.description
    return CatalogueBatchItem(
        source="govdata",
        external_id=external_id,
        jurisdiction_id=jurisdiction_id,
        title_i18n={"de": title},
        description_i18n={"de": description} if description else None,
        portal_url=row.url,
        raw_payload=dict(row.raw),
    )


def _external_id_for_row(row: GovDataRow) -> str:
    parts = row.external_id_parts
    if parts is None:
        raise GovDataMappingError("row has no external id (leika_key, ozgid, or id)")
    namespace, value = parts
    return f"govdata:{namespace}:{value}"


def _jurisdiction_id_for_row(row: GovDataRow, *, federal_jurisdiction_id: UUID) -> UUID:
    ars = row.ars
    if ars is None or ars == FEDERAL_ARS:
        return federal_jurisdiction_id
    raise GovDataMappingError(f"unsupported ars jurisdiction scope: {ars}")
