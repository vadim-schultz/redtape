"""Catalogue ingest: each source yields batches of mapped rows, and one function posts them."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol
from uuid import UUID

from discovery_ingest.catalogue_scope import FEDERAL_ARS
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.govdata.client import GovDataMappingError, GovDataOzgClient, map_govdata_record
from discovery_ingest.govdata.models import GovDataRow
from discovery_ingest.operations.results import IngestResult
from discovery_ingest.pvog.client import PvogMappingError, map_pvog_record
from discovery_ingest.pvog.models import PvogRecord
from discovery_ingest.schemas import CatalogueBatchItem


class NothingToIngest(Exception):
    """A source produced no mappable row; the message names the source for the operator."""

    def __init__(self, source_name: str) -> None:
        """Name the source whose rows were all skipped or absent."""
        super().__init__(f"no mappable {source_name} rows")


@dataclass(frozen=True, slots=True)
class SourceBatch:
    """The mapped rows of one unit of a source, and the messages of the rows that could not be mapped."""

    items: list[CatalogueBatchItem] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


class CatalogueSource(Protocol):
    """One origin of catalogue rows; ``name`` is the label the messages use."""

    name: str

    def batches(self) -> Iterator[SourceBatch]:
        """Yield the batches in the order they must be posted."""
        ...


class GovDataRecordPages(Protocol):
    """The CKAN feed pages of GovData Leistungen rows."""

    def iter_record_pages(
        self, *, max_pages: int, page_size: int, max_records: int | None
    ) -> Iterator[list[GovDataRow]]:
        """Yield each page of rows under the caps."""
        ...


class PvogRecordWalk(Protocol):
    """The PVOG Suchdienst row walk, yielding ``(personal_matter_code, record)``."""

    def iter_records(self, *, ars: str, max_pages: int | None) -> Iterator[tuple[str, PvogRecord]]:
        """Yield the rows of the federal scope under the page cap."""
        ...


def _govdata_batch(rows: list[GovDataRow], jurisdiction_id: UUID) -> SourceBatch:
    items: list[CatalogueBatchItem] = []
    skipped: list[str] = []
    for row in rows:
        try:
            items.append(map_govdata_record(row, federal_jurisdiction_id=jurisdiction_id))
        except GovDataMappingError as err:
            skipped.append(str(err))
    return SourceBatch(items=items, skipped=skipped)


class GovDataFileSource:
    """The rows of one Leistungen JSON export file, as a single batch."""

    name = "GovData"

    def __init__(self, path: Path, jurisdiction_id: UUID) -> None:
        """Keep the export path and the jurisdiction of the federal rows."""
        self._path = path
        self._jurisdiction_id = jurisdiction_id

    def batches(self) -> Iterator[SourceBatch]:
        """Load the export and yield its mapped rows as one batch."""
        ozg = GovDataOzgClient.from_json_file(self._path)
        yield _govdata_batch(ozg.records, self._jurisdiction_id)


class GovDataCkanSource:
    """The rows of the GovData CKAN feed, one batch per feed page, so each page is posted as it arrives."""

    name = "GovData"

    def __init__(
        self,
        ckan: GovDataRecordPages,
        jurisdiction_id: UUID,
        *,
        max_pages: int,
        page_size: int,
        max_records: int | None = None,
    ) -> None:
        """Keep the feed client, the jurisdiction and the page and record caps of the run."""
        self._ckan = ckan
        self._jurisdiction_id = jurisdiction_id
        self._max_pages = max_pages
        self._page_size = page_size
        self._max_records = max_records

    def batches(self) -> Iterator[SourceBatch]:
        """Yield one mapped batch for each feed page the client returns."""
        for page in self._ckan.iter_record_pages(
            max_pages=self._max_pages,
            page_size=self._page_size,
            max_records=self._max_records,
        ):
            yield _govdata_batch(page, self._jurisdiction_id)


class PvogSource:
    """The PVOG federal rows: every page is walked before one batch is yielded, so a late failure posts nothing."""

    name = "PVOG"

    def __init__(self, walk: PvogRecordWalk, jurisdiction_id: UUID, *, max_pages: int | None) -> None:
        """Keep the row walk, the jurisdiction of the federal rows and the optional page cap."""
        self._walk = walk
        self._jurisdiction_id = jurisdiction_id
        self._max_pages = max_pages

    def batches(self) -> Iterator[SourceBatch]:
        """Walk the federal scope and yield every mapped row as one batch."""
        items: list[CatalogueBatchItem] = []
        skipped: list[str] = []
        for code, row in self._walk.iter_records(ars=FEDERAL_ARS, max_pages=self._max_pages):
            try:
                items.append(
                    map_pvog_record(
                        row,
                        jurisdiction_id=self._jurisdiction_id,
                        personal_matter_code=code,
                        personal_matter_path=row.source_path,
                    )
                )
            except PvogMappingError as err:
                skipped.append(str(err))
        yield SourceBatch(items=items, skipped=skipped)


def ingest(
    source: CatalogueSource,
    client: DiscoveryIngestClient,
    *,
    on_skip: Callable[[str], None] | None = None,
) -> IngestResult:
    """Post every non-empty batch of ``source`` in order and return the counts.

    ``on_skip`` receives each skipped row's message before the batch that follows it is posted. Raises
    :class:`NothingToIngest` when no row was mappable; a refused post raises the machine API error.
    """
    skipped: list[str] = []
    rows_posted = 0
    for batch in source.batches():
        for message in batch.skipped:
            if on_skip is not None:
                on_skip(message)
        skipped.extend(batch.skipped)
        if batch.items:
            client.catalogue.upsert_batches(batch.items)
            rows_posted += len(batch.items)
    if rows_posted == 0:
        raise NothingToIngest(source.name)
    return IngestResult(source=source.name, rows_posted=rows_posted, rows_skipped=len(skipped), skipped=skipped)
