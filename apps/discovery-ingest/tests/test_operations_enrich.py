"""Enrich operations · one entity-and-claims sequence for FIM and LeiKa, with typed errors and no printing."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from discovery_ingest.catalogue_export import CatalogueExportItem
from discovery_ingest.client import DiscoveryMachineApiError
from discovery_ingest.fim.client import FixtureSteckbriefSource, HttpSteckbriefSource
from discovery_ingest.fim.models import Stammtext, Steckbrief
from discovery_ingest.leika.client import FixtureStammtextSource
from discovery_ingest.operations.enrich import (
    CatalogueRowNotFound,
    EnrichFetchError,
    FimEnricher,
    LeikaEnricher,
    MissingLookupKey,
    catalogue_row,
    post_enrichment,
    run_enrich,
)

FIXTURES = Path(__file__).parent / "fixtures"
FIM_BASE = "https://fimportal.de"
ENTITY_ID = uuid.UUID("33333333-3333-3333-3333-333333333301")
CATALOGUE_ID = uuid.UUID("22222222-2222-2222-2222-222222222201")
FIM_KEY = "99096049001001"


class FakeCatalogueApi:
    """Records the entity and claim bodies; can refuse the claims."""

    def __init__(self, *, refuse_claims: bool = False) -> None:
        self.entities: list[object] = []
        self.claims: list[object] = []
        self._refuse_claims = refuse_claims

    def upsert_entity(self, body: object) -> SimpleNamespace:
        self.entities.append(body)
        return SimpleNamespace(id=ENTITY_ID)

    def append_claim(self, body: object) -> None:
        if self._refuse_claims:
            raise DiscoveryMachineApiError(422, "claim refused")
        self.claims.append(body)


class FakeClient:
    def __init__(self, catalogue: FakeCatalogueApi) -> None:
        self.catalogue = catalogue


def _catalogue(raw_payload: dict[str, object] | None = None) -> CatalogueExportItem:
    return CatalogueExportItem(
        id=CATALOGUE_ID,
        source="fim",
        portal_url=None,
        title_i18n={"de": "Leistung"},
        raw_payload=raw_payload if raw_payload is not None else {"fim_id": FIM_KEY},
    )


def _steckbrief() -> Steckbrief:
    body = json.loads((FIXTURES / "fim" / "steckbrief.json").read_text(encoding="utf-8"))
    return Steckbrief.from_object(body)


def _stammtext() -> Stammtext:
    body = json.loads((FIXTURES / "leika" / "stammtext.json").read_text(encoding="utf-8"))
    return Stammtext.from_object(body)


def _fim_enricher(steckbrief: Steckbrief | None = None) -> FimEnricher:
    source = FixtureSteckbriefSource(steckbrief or _steckbrief())
    return FimEnricher(source, FIM_BASE)


def _leika_enricher() -> LeikaEnricher:
    return LeikaEnricher(FixtureStammtextSource(_stammtext()), FIM_BASE)


def test_run_enrich_posts_entity_then_claims_for_fim(capsys: pytest.CaptureFixture[str]) -> None:
    """run_enrich · the FIM enricher posts one entity, then its claims, through the one sequence."""
    api = FakeCatalogueApi()

    result = run_enrich(_fim_enricher(), _catalogue(), FakeClient(api))

    assert len(api.entities) == 1
    assert len(api.claims) >= 1
    assert result.entity_id == ENTITY_ID
    assert result.claims_posted == len(api.claims)
    assert capsys.readouterr() == ("", "")


def test_run_enrich_posts_entity_then_claims_for_leika(capsys: pytest.CaptureFixture[str]) -> None:
    """run_enrich · the LeiKa enricher posts one entity and its claims through the same function."""
    api = FakeCatalogueApi()
    catalogue = _catalogue({"redaktion_id": "RED-EXAMPLE", "leistung_id": "LB-EXAMPLE-001"})

    result = run_enrich(_leika_enricher(), catalogue, FakeClient(api))

    assert len(api.entities) == 1
    assert result.claims_posted == len(api.claims) >= 1
    assert capsys.readouterr() == ("", "")


def test_run_enrich_raises_missing_lookup_key_with_the_existing_message() -> None:
    """run_enrich · a catalogue row without a steckbrief key raises MissingLookupKey with the old text."""
    api = FakeCatalogueApi()

    with pytest.raises(MissingLookupKey, match="no steckbrief key"):
        run_enrich(_fim_enricher(), _catalogue({"fim_id": "LB-EXAMPLE-STECK"}), FakeClient(api))
    assert api.entities == []


def test_run_enrich_raises_missing_lookup_key_for_leika_without_segments() -> None:
    """run_enrich · a LeiKa row without redaktion or leistung raises MissingLookupKey."""
    with pytest.raises(MissingLookupKey, match="missing redaktion_id and leistung_id"):
        run_enrich(_leika_enricher(), _catalogue({}), FakeClient(FakeCatalogueApi()))


def test_run_enrich_raises_enrich_fetch_error_on_fixture_mismatch() -> None:
    """run_enrich · a fixture for another key raises EnrichFetchError carrying the fim message."""
    other = Steckbrief.from_object({"leistungsschluessel": "99154021000000"})
    enricher = FimEnricher(FixtureSteckbriefSource(other), FIM_BASE)

    with pytest.raises(EnrichFetchError, match="^fim fetch failed: fixture key"):
        run_enrich(enricher, _catalogue(), FakeClient(FakeCatalogueApi()))


def test_run_enrich_raises_enrich_fetch_error_on_a_leika_fixture_mismatch() -> None:
    """run_enrich · a LeiKa fixture for other segments raises EnrichFetchError with the leika message."""
    catalogue = _catalogue({"redaktion_id": "OTHER", "leistung_id": "LB-EXAMPLE-001"})

    with pytest.raises(EnrichFetchError, match="^leika fetch failed: fixture segments do not match"):
        run_enrich(_leika_enricher(), catalogue, FakeClient(FakeCatalogueApi()))


def test_run_enrich_fetches_live_through_the_http_source() -> None:
    """run_enrich · a live source is asked for the lookup key and its steckbrief is mapped."""
    body = {"leistungsschluessel": FIM_KEY, "titel": "Live-Leistung"}
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json=body)

    source = HttpSteckbriefSource(FIM_BASE, http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    api = FakeCatalogueApi()

    run_enrich(FimEnricher(source, FIM_BASE), _catalogue(), FakeClient(api))

    assert seen == [f"{FIM_BASE}/api/v1/leistung-steckbriefe/{FIM_KEY}"]
    assert api.entities


def test_post_enrichment_stops_at_the_first_api_error_after_the_entity() -> None:
    """post_enrichment · a refused claim stops the sequence; the entity was already posted."""
    api = FakeCatalogueApi(refuse_claims=True)
    enricher = _fim_enricher()

    with pytest.raises(DiscoveryMachineApiError):
        post_enrichment(enricher, _catalogue(), enricher.fetch(enricher.lookup(_catalogue())), FakeClient(api))

    assert len(api.entities) == 1
    assert api.claims == []


def test_catalogue_row_raises_not_found_for_an_unknown_id(tmp_path: Path) -> None:
    """catalogue_row · an id that is not in the export raises CatalogueRowNotFound."""
    export = tmp_path / "export.json"
    export.write_text('{"items": []}', encoding="utf-8")

    with pytest.raises(CatalogueRowNotFound, match="catalogue service id not found in export"):
        catalogue_row(export, CATALOGUE_ID)


def test_operations_enrich_module_imports_no_output_library() -> None:
    """operations · the enrich module imports no argparse, typer, rich or sys."""
    import ast

    source = Path(__file__).parents[1] / "discovery_ingest" / "operations" / "enrich.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    names = {
        alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names
    }
    names |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    assert not names & {"argparse", "typer", "rich", "sys"}
