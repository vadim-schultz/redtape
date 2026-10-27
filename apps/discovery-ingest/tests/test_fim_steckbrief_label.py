"""Steckbrief entity label and claim tests against the real response shape (follow-up to chapter 12)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from discovery_ingest.catalogue_export import CatalogueExportItem
from discovery_ingest.enrich import fim_steckbrief_claim_requests, fim_steckbrief_entity_request

FIXTURE = Path(__file__).parent / "fixtures" / "fim" / "steckbrief.json"
FIM_BASE = "https://fimportal.de"
KEY = "99096049001001"
CATALOGUE = CatalogueExportItem(
    id=uuid.UUID("22222222-2222-2222-2222-222222222201"),
    source="govdata",
    title_i18n={"de": "Katalogtitel"},
    raw_payload={"leika_key": KEY},
)
ENTITY_ID = uuid.UUID("33333333-3333-3333-3333-333333333301")


def _real() -> dict[str, object]:
    return dict(json.loads(FIXTURE.read_text(encoding="utf-8")))


def _label(steckbrief: dict[str, object]) -> str | None:
    return fim_steckbrief_entity_request(CATALOGUE, steckbrief, fim_base_url=FIM_BASE).label


def _kinds(steckbrief: dict[str, object]) -> list[str]:
    claims = fim_steckbrief_claim_requests(CATALOGUE, steckbrief, entity_id=ENTITY_ID, fim_base_url=FIM_BASE)
    return [claim.kind for claim in claims]


def test_the_real_steckbrief_yields_its_title_as_the_label() -> None:
    """real fixture · the entity label is the top-level title."""
    real = _real()
    assert "titel" not in real
    assert _label(real) == real["title"]
    assert _label(real) == "Short Range Certificate (SRC) Erteilung nach Prüfung"


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        ({"title": "Neu", "titel": "Alt", "leistungsbezeichnung": "Bezeichnung"}, "Neu"),
        ({"titel": "Alt", "leistungsbezeichnung": "Bezeichnung"}, "Alt"),
        ({"leistungsbezeichnung": " Bezeichnung "}, "Bezeichnung"),
        ({"title": "  ", "titel": "Alt"}, "Alt"),
        ({"title": 7, "leistungsbezeichnung": "Bezeichnung"}, "Bezeichnung"),
    ],
)
def test_the_label_falls_back_from_title_to_titel_to_leistungsbezeichnung(
    fields: dict[str, object],
    expected: str,
) -> None:
    """label · title, then legacy titel, then leistungsbezeichnung; blank or non-string values are skipped."""
    assert _label({"leistungsschluessel": KEY, **fields}) == expected


@pytest.mark.parametrize("fields", [{}, {"title": None, "titel": ""}, {"title": 3, "leistungsbezeichnung": []}])
def test_a_steckbrief_without_any_title_field_has_no_label_and_does_not_crash(fields: dict[str, object]) -> None:
    """label · none of the title fields yields no label (the entity is still built)."""
    request = fim_steckbrief_entity_request(CATALOGUE, {"leistungsschluessel": KEY, **fields}, fim_base_url=FIM_BASE)
    assert request.label is None
    assert request.canonical_url.endswith(f"/leistung-steckbriefe/{KEY}")


def test_the_real_steckbrief_has_no_kurztext_so_it_yields_no_metadata_claim() -> None:
    """claims · without kurztext only the new_document claim is built and nothing is invented from title."""
    assert _kinds(_real()) == ["new_document"]


def test_a_steckbrief_with_a_kurztext_still_yields_the_metadata_claim() -> None:
    """claims · a real kurztext keeps the unchanged metadata claim shape."""
    steckbrief = {**_real(), "kurztext": " Kurzbeschreibung "}
    claims = fim_steckbrief_claim_requests(CATALOGUE, steckbrief, entity_id=ENTITY_ID, fim_base_url=FIM_BASE)
    assert [claim.kind for claim in claims] == ["metadata", "new_document"]
    assert claims[0].payload == {"kurztext": "Kurzbeschreibung"}
