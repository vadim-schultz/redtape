"""Catalogue operations · one ingest over three sources, typed results, typed failures and no output."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from discovery_ingest.client import DiscoveryMachineApiError
from discovery_ingest.govdata.ckan import GovDataCkanError
from discovery_ingest.govdata.models import GovDataRow, OzgPage
from discovery_ingest.operations.catalogue import (
    GovDataCkanSource,
    GovDataFileSource,
    NothingToIngest,
    PvogSource,
    ingest,
)
from discovery_ingest.pvog.client import PvogClientError
from discovery_ingest.pvog.models import PvogPage, PvogRecord
from discovery_ingest.schemas import CatalogueBatchItem

GOVDATA_FIXTURES = Path(__file__).parent / "fixtures" / "govdata"
PVOG_FIXTURES = Path(__file__).parent / "fixtures" / "pvog"
JURISDICTION = uuid.UUID("11111111-1111-1111-1111-111111111101")


class FakeCatalogueApi:
    """Records each batch posted through ``upsert_batches``; can refuse the next post."""

    def __init__(self, *, refuse: bool = False) -> None:
        self.batches: list[list[CatalogueBatchItem]] = []
        self._refuse = refuse

    def upsert_batches(self, items: list[CatalogueBatchItem]) -> None:
        if self._refuse:
            raise DiscoveryMachineApiError(422, "refused")
        self.batches.append(list(items))


class FakeClient:
    def __init__(self, api: FakeCatalogueApi) -> None:
        self.catalogue = api


def _govdata_rows() -> list[GovDataRow]:
    """Two rows: one mappable (with a leika key) and one without an identifier (skipped)."""
    page = json.loads((GOVDATA_FIXTURES / "ozg_page.json").read_text(encoding="utf-8"))
    return OzgPage.model_validate(page).content


def _pvog_records() -> list[tuple[str, PvogRecord]]:
    page = json.loads((PVOG_FIXTURES / "v7_page_paged_code.json").read_text(encoding="utf-8"))
    records, _ = PvogPage.model_validate(page).records_and_last
    return [("LEAF_A", record) for record in records]


class FakeCkan:
    """Yields the given pages as the CKAN client does, recording the caps it was asked for."""

    def __init__(self, pages: list[list[GovDataRow]], *, fail_after: int | None = None) -> None:
        self._pages = pages
        self._fail_after = fail_after
        self.caps: tuple[int, int, int | None] | None = None

    def iter_record_pages(
        self, *, max_pages: int, page_size: int = 100, max_records: int | None = None
    ) -> Iterator[list[GovDataRow]]:
        self.caps = (max_pages, page_size, max_records)
        for index, page in enumerate(self._pages):
            if self._fail_after is not None and index == self._fail_after:
                raise GovDataCkanError("GovData HTTP 503 for https://ckan.test")
            yield page


class FakePvog:
    def __init__(self, records: list[tuple[str, PvogRecord]], *, fail: bool = False) -> None:
        self._records = records
        self._fail = fail

    def iter_records(self, *, ars: str, max_pages: int | None) -> Iterator[tuple[str, PvogRecord]]:
        yield from self._records
        if self._fail:
            raise PvogClientError("PVOG Suchdienst HTTP 500")


def test_ingest_returns_counts_and_skips_for_each_source(tmp_path: Path) -> None:
    """ingest · each of the three sources posts its mappable rows and reports its skips."""
    export = tmp_path / "ozg.json"
    export.write_text((GOVDATA_FIXTURES / "ozg_page.json").read_text(encoding="utf-8"), encoding="utf-8")
    sources = [
        GovDataFileSource(export, JURISDICTION),
        GovDataCkanSource(FakeCkan([_govdata_rows()]), JURISDICTION, max_pages=1, page_size=100),
        PvogSource(FakePvog(_pvog_records()), JURISDICTION, max_pages=None, mapping_version="category-contract-v1"),
    ]

    results = [ingest(source, FakeClient(FakeCatalogueApi())) for source in sources]

    assert [result.source for result in results] == ["GovData", "GovData", "PVOG"]
    assert all(result.rows_posted >= 1 for result in results)
    assert results[0].rows_skipped == 1
    assert len(results[0].skipped) == 1


def test_ingest_reports_each_skip_before_the_post_that_follows_it() -> None:
    """ingest · every skip reaches the callback, batch by batch, before that batch is posted."""
    events: list[str] = []

    class Recording(FakeCatalogueApi):
        def upsert_batches(self, items: list[CatalogueBatchItem]) -> None:
            events.append("post")
            super().upsert_batches(items)

    source = GovDataCkanSource(FakeCkan([_govdata_rows()]), JURISDICTION, max_pages=1, page_size=100)
    result = ingest(source, FakeClient(Recording()), on_skip=lambda message: events.append(f"skip:{message}"))

    assert events[0].startswith("skip:")
    assert events[-1] == "post"
    assert result.rows_skipped == 1


def test_ingest_raises_nothing_to_ingest_when_every_row_is_skipped(tmp_path: Path) -> None:
    """ingest · a source whose rows are all skipped raises NothingToIngest with the old message."""
    rows = [GovDataRow.model_validate({"leistungsname": "Ohne Kennung"})]
    source = GovDataCkanSource(FakeCkan([rows]), JURISDICTION, max_pages=1, page_size=100)

    with pytest.raises(NothingToIngest, match="^no mappable GovData rows$"):
        ingest(source, FakeClient(FakeCatalogueApi()))


def test_ingest_propagates_machine_api_error() -> None:
    """ingest · a refused post propagates the machine API error unchanged."""
    source = GovDataCkanSource(FakeCkan([_govdata_rows()]), JURISDICTION, max_pages=1, page_size=100)

    with pytest.raises(DiscoveryMachineApiError):
        ingest(source, FakeClient(FakeCatalogueApi(refuse=True)))


def test_ingest_propagates_the_source_failure_after_earlier_pages_posted() -> None:
    """ingest · a page that fails after an earlier page was posted keeps the earlier post and raises the source error."""
    api = FakeCatalogueApi()
    source = GovDataCkanSource(
        FakeCkan([_govdata_rows(), _govdata_rows()], fail_after=1), JURISDICTION, max_pages=5, page_size=2
    )

    with pytest.raises(GovDataCkanError, match="503"):
        ingest(source, FakeClient(api))
    assert len(api.batches) == 1


def test_pvog_source_posts_nothing_when_a_late_page_fails() -> None:
    """ingest · PVOG walks every page before its single post, so a late failure posts nothing."""
    api = FakeCatalogueApi()
    source = PvogSource(
        FakePvog(_pvog_records(), fail=True), JURISDICTION, max_pages=None, mapping_version="category-contract-v1"
    )

    with pytest.raises(PvogClientError):
        ingest(source, FakeClient(api))
    assert api.batches == []


def test_govdata_ckan_source_passes_its_caps_to_the_client() -> None:
    """GovDataCkanSource · max_pages, page size and max_records reach the client unchanged."""
    ckan = FakeCkan([])
    source = GovDataCkanSource(ckan, JURISDICTION, max_pages=3, page_size=7, max_records=9)

    with pytest.raises(NothingToIngest):
        ingest(source, FakeClient(FakeCatalogueApi()))
    assert ckan.caps == (3, 7, 9)


def test_ingest_posts_one_batch_per_non_empty_source_batch() -> None:
    """ingest · an empty batch is not posted; each non-empty batch is posted once."""
    api = FakeCatalogueApi()
    source = GovDataCkanSource(FakeCkan([[], _govdata_rows(), []]), JURISDICTION, max_pages=3, page_size=100)

    ingest(source, FakeClient(api))

    assert len(api.batches) == 1


def test_operations_catalogue_module_imports_no_output_library() -> None:
    """operations · the catalogue module imports no argparse, typer, rich or sys."""
    import ast

    source = Path(__file__).parents[1] / "discovery_ingest" / "operations" / "catalogue.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    names = {
        alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names
    }
    names |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    assert not names & {"argparse", "typer", "rich", "sys"}
