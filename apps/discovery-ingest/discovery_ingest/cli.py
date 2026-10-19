"""CLI entry points for discovery ingest workers."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import UUID

from discovery_ingest.api_client import DiscoveryMachineApiError, DiscoveryMachineClient, _post_catalogue_batches
from discovery_ingest.catalogue_export import load_catalogue_row
from discovery_ingest.config import IngestSettings, load_ingest_settings
from discovery_ingest.enrich import (
    fim_id_from_catalogue,
    fim_steckbrief_claim_requests,
    fim_steckbrief_entity_request,
    leika_segments_from_catalogue,
    leika_stammtext_claim_requests,
    leika_stammtext_entity_request,
)
from discovery_ingest.fim.client import FimClientError, FimSteckbriefClient
from discovery_ingest.govdata.ckan import GovDataCkanClient, GovDataCkanError
from discovery_ingest.govdata.client import GovDataMappingError, GovDataOzgClient, _map_govdata_record
from discovery_ingest.leika.client import LeikaClientError, LeikaStammtextClient
from discovery_ingest.pvog.client import FEDERAL_ARS, PvogClient, PvogMappingError, map_pvog_record
from discovery_ingest.schemas import CatalogueBatchItem
from discovery_ingest.worker.drain import run_worker_drain
from discovery_ingest.worker.fetcher import PoliteUrlFetcher


def main(argv: list[str] | None = None) -> int:
    """Run a discovery ingest subcommand."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2
    if args.command == "govdata" and args.govdata_command == "run":
        return _govdata_run(args)
    if args.command == "govdata" and args.govdata_command == "fetch":
        return _govdata_fetch(args)
    if args.command == "pvog" and args.pvog_command == "run":
        return _pvog_run(args)
    if args.command == "fim" and args.fim_command == "enrich":
        return _fim_enrich(args)
    if args.command == "leika" and args.leika_command == "enrich":
        return _leika_enrich(args)
    if args.command == "worker" and args.worker_command == "drain":
        return _worker_drain(args)
    parser.print_help()
    return 2


def _govdata_run(args: argparse.Namespace) -> int:
    settings = load_ingest_settings()
    ozg = GovDataOzgClient.from_json_file(Path(args.input))
    items = _map_govdata_records(ozg.records, federal_jurisdiction_id=args.jurisdiction_id)
    if not items:
        print("no mappable GovData rows", file=sys.stderr)
        return 1
    try:
        _post_catalogue_batches(
            settings.discovery_api_url,
            settings.discovery_api_key,
            items,
        )
    except DiscoveryMachineApiError:
        return 1
    return 0


def _govdata_fetch(args: argparse.Namespace) -> int:
    settings = load_ingest_settings()
    ckan = GovDataCkanClient(
        settings.govdata_ckan_base_url,
        settings.govdata_package_id,
        scope_ars=settings.govdata_open_pvog_ars,
    )
    try:
        return _govdata_fetch_pages(
            ckan,
            settings=settings,
            jurisdiction_id=args.jurisdiction_id,
            max_pages=args.max_pages,
            page_size=args.page_size,
            max_records=args.max_records,
        )
    except GovDataCkanError as err:
        print(f"govdata fetch failed: {err}", file=sys.stderr)
        return 1


def _govdata_fetch_pages(
    ckan: GovDataCkanClient,
    *,
    settings: IngestSettings,
    jurisdiction_id: UUID,
    max_pages: int,
    page_size: int,
    max_records: int | None,
) -> int:
    posted_any = False
    for page_records in ckan.iter_record_pages(
        max_pages=max_pages,
        page_size=page_size,
        max_records=max_records,
    ):
        items = _map_govdata_records(page_records, federal_jurisdiction_id=jurisdiction_id)
        if not items:
            continue
        try:
            _post_catalogue_batches(
                settings.discovery_api_url,
                settings.discovery_api_key,
                items,
            )
        except DiscoveryMachineApiError as err:
            print(err, file=sys.stderr)
            return 1
        posted_any = True
    if not posted_any:
        print("no mappable GovData rows", file=sys.stderr)
        return 1
    return 0


def _pvog_run(args: argparse.Namespace) -> int:
    settings = load_ingest_settings()
    pvog = PvogClient(settings.pvog_api_base_url)
    items = _map_pvog_records(
        pvog.iter_records(ars=FEDERAL_ARS, max_pages=args.max_pages),
        jurisdiction_id=args.jurisdiction_id,
    )
    if not items:
        print("no mappable PVOG rows", file=sys.stderr)
        return 1
    try:
        _post_catalogue_batches(
            settings.discovery_api_url,
            settings.discovery_api_key,
            items,
        )
    except DiscoveryMachineApiError:
        return 1
    return 0


def _fim_enrich(args: argparse.Namespace) -> int:
    settings = load_ingest_settings()
    catalogue = load_catalogue_row(Path(args.catalogue_export), args.catalogue_service_id)
    if catalogue is None:
        print("catalogue service id not found in export", file=sys.stderr)
        return 1
    fim_id = fim_id_from_catalogue(catalogue)
    if fim_id is None:
        print("catalogue row has no fim_id or leistungsschluessel", file=sys.stderr)
        return 1
    fim = FimSteckbriefClient.from_json_file(Path(args.input), base_url=settings.fim_portal_base_url)
    try:
        steckbrief = fim.fetch_steckbrief(fim_id)
    except FimClientError as err:
        print(f"fim fetch failed: {err}", file=sys.stderr)
        return 1
    entity_body = fim_steckbrief_entity_request(catalogue, steckbrief, fim_base_url=settings.fim_portal_base_url)
    api = DiscoveryMachineClient(settings.discovery_api_url, settings.discovery_api_key)
    try:
        entity = api.post_entity(entity_body)
        for claim in fim_steckbrief_claim_requests(
            catalogue,
            steckbrief,
            entity_id=entity.id,
            fim_base_url=settings.fim_portal_base_url,
        ):
            api.post_claim(claim)
    except DiscoveryMachineApiError:
        return 1
    return 0


def _worker_drain(args: argparse.Namespace) -> int:
    settings = load_ingest_settings()
    client = DiscoveryMachineClient(settings.discovery_api_url, settings.discovery_api_key)
    fetcher = PoliteUrlFetcher()
    try:
        report = run_worker_drain(client, fetcher, max_tasks=args.max_tasks)
    except DiscoveryMachineApiError:
        return 1
    print(json.dumps(report.model_dump(mode="json")))
    return 0


def _leika_enrich(args: argparse.Namespace) -> int:
    settings = load_ingest_settings()
    catalogue = load_catalogue_row(Path(args.catalogue_export), args.catalogue_service_id)
    if catalogue is None:
        print("catalogue service id not found in export", file=sys.stderr)
        return 1
    segments = leika_segments_from_catalogue(catalogue)
    if segments is None:
        print("catalogue row missing redaktion_id and leistung_id", file=sys.stderr)
        return 1
    redaktion_id, leistung_id = segments
    leika = LeikaStammtextClient.from_json_file(Path(args.input), base_url=settings.fim_portal_base_url)
    try:
        stammtext = leika.fetch_stammtext(redaktion_id, leistung_id)
    except LeikaClientError as err:
        print(f"leika fetch failed: {err}", file=sys.stderr)
        return 1
    entity_body = leika_stammtext_entity_request(catalogue, stammtext, fim_base_url=settings.fim_portal_base_url)
    api = DiscoveryMachineClient(settings.discovery_api_url, settings.discovery_api_key)
    try:
        entity = api.post_entity(entity_body)
        for claim in leika_stammtext_claim_requests(
            catalogue,
            stammtext,
            entity_id=entity.id,
            fim_base_url=settings.fim_portal_base_url,
        ):
            api.post_claim(claim)
    except DiscoveryMachineApiError:
        return 1
    return 0


def _map_govdata_records(
    records: list[dict[str, Any]],
    *,
    federal_jurisdiction_id: UUID,
) -> list[CatalogueBatchItem]:
    items: list[CatalogueBatchItem] = []
    for row in records:
        try:
            items.append(
                _map_govdata_record(row, federal_jurisdiction_id=federal_jurisdiction_id),
            )
        except GovDataMappingError as err:
            print(f"skip row: {err}", file=sys.stderr)
    return items


def _map_pvog_records(
    records: Iterator[dict[str, Any]],
    *,
    jurisdiction_id: UUID,
) -> list[CatalogueBatchItem]:
    items: list[CatalogueBatchItem] = []
    for row in records:
        try:
            items.append(map_pvog_record(row, jurisdiction_id=jurisdiction_id))
        except PvogMappingError as err:
            print(f"skip row: {err}", file=sys.stderr)
    return items


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="discovery_ingest")
    sub = parser.add_subparsers(dest="command")

    govdata = sub.add_parser("govdata", help="GovData OZG catalogue ingest")
    govdata_sub = govdata.add_subparsers(dest="govdata_command")
    run = govdata_sub.add_parser("run", help="Upsert rows from a Leistungen JSON export")
    run.add_argument("--input", required=True, help="Path to OZG Leistungen JSON page")
    run.add_argument(
        "--jurisdiction-id",
        type=UUID,
        required=True,
        help="Jurisdiction UUID for federal rows (ars 000000000000)",
    )
    fetch = govdata_sub.add_parser("fetch", help="Fetch OZG Leistungen from GovData CKAN and upsert")
    fetch.add_argument(
        "--jurisdiction-id",
        type=UUID,
        required=True,
        help="Jurisdiction UUID for federal rows (ars 000000000000)",
    )
    fetch.add_argument(
        "--max-pages",
        type=int,
        default=150,
        help="Maximum Leistungen feed pages per run (default 150)",
    )
    fetch.add_argument(
        "--page-size",
        type=int,
        default=100,
        help="Rows per Leistungen feed page (default 100)",
    )
    fetch.add_argument(
        "--max-records",
        type=int,
        default=None,
        help="Optional safety cap on total rows fetched",
    )

    pvog = sub.add_parser("pvog", help="PVOG Suchdienst catalogue ingest")
    pvog_sub = pvog.add_subparsers(dest="pvog_command")
    pvog_run = pvog_sub.add_parser("run", help="Upsert rows from PVOG Suchdienst API")
    pvog_run.add_argument(
        "--jurisdiction-id",
        type=UUID,
        required=True,
        help="Jurisdiction UUID for federal scope (ars 000000000000)",
    )
    pvog_run.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional cap on PVOG pagination pages per run",
    )

    fim = sub.add_parser("fim", help="FIM Portal enrich")
    fim_sub = fim.add_subparsers(dest="fim_command")
    fim_enrich = fim_sub.add_parser("enrich", help="Upsert entity and claims from steckbrief")
    fim_enrich.add_argument("--catalogue-service-id", type=UUID, required=True)
    fim_enrich.add_argument("--catalogue-export", required=True, help="Admin catalogue export JSON")
    fim_enrich.add_argument("--input", required=True, help="Steckbrief JSON fixture or snapshot")

    leika = sub.add_parser("leika", help="LeiKa stammtext enrich")
    leika_sub = leika.add_subparsers(dest="leika_command")
    leika_enrich = leika_sub.add_parser("enrich", help="Upsert entity and claims from LeiKa stammtext")
    leika_enrich.add_argument("--catalogue-service-id", type=UUID, required=True)
    leika_enrich.add_argument("--catalogue-export", required=True, help="Admin catalogue export JSON")
    leika_enrich.add_argument("--input", required=True, help="Stammtext JSON fixture or snapshot")

    worker = sub.add_parser("worker", help="Discovery task worker")
    worker_sub = worker.add_subparsers(dest="worker_command")
    worker_drain = worker_sub.add_parser("drain", help="Claim tasks, fetch URLs, complete or fail")
    worker_drain.add_argument(
        "--max-tasks",
        type=int,
        default=50,
        help="Maximum tasks to claim per run (1–50, default 50)",
    )
    return parser
