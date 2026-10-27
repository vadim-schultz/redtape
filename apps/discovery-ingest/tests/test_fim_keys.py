"""Steckbrief key resolution agrees with the API fanout on the shared case table (chapter 12)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from discovery_ingest.catalogue_export import CatalogueExportItem
from discovery_ingest.enrich import fim_id_from_catalogue
from discovery_ingest.fim.keys import steckbrief_key

CASES_PATH = Path(__file__).parents[2] / "api" / "tests" / "fixtures" / "steckbrief_key_cases.json"
CASES: list[dict[str, object]] = json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]
IDS = [str(case["name"]) for case in CASES]


def _catalogue(raw_payload: dict[str, object]) -> CatalogueExportItem:
    return CatalogueExportItem(id=uuid.uuid4(), source="govdata", raw_payload=raw_payload)  # type: ignore[arg-type]


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_steckbrief_key_follows_the_shared_case_table(case: dict[str, object]) -> None:
    """steckbrief key · follows the case table shared with the api fanout."""
    assert steckbrief_key(case["raw_payload"]) == case["key"]  # type: ignore[arg-type]


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_fim_id_from_catalogue_uses_the_same_resolution(case: dict[str, object]) -> None:
    """fim_id_from_catalogue · resolves exactly like the fanout key resolver."""
    assert fim_id_from_catalogue(_catalogue(case["raw_payload"])) == case["key"]  # type: ignore[arg-type]
