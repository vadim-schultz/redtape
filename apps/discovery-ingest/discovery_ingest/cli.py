"""CLI entry points for discovery ingest workers."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

from discovery_ingest.api_client import DiscoveryMachineApiError, DiscoveryMachineClient
from discovery_ingest.config import load_ingest_settings
from discovery_ingest.govdata.client import GovDataMappingError, GovDataOzgClient, _map_govdata_record
from discovery_ingest.schemas import CatalogueBatchItem


def main(argv: list[str] | None = None) -> int:
    """Run a discovery ingest subcommand."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2
    if args.command == "govdata" and args.govdata_command == "run":
        return _govdata_run(args)
    parser.print_help()
    return 2


def _govdata_run(args: argparse.Namespace) -> int:
    settings = load_ingest_settings()
    client = DiscoveryMachineClient(settings.discovery_api_url, settings.discovery_api_key)
    ozg = GovDataOzgClient.from_json_file(Path(args.input))
    items = _map_govdata_records(ozg.records, federal_jurisdiction_id=args.jurisdiction_id)
    if not items:
        print("no mappable GovData rows", file=sys.stderr)
        return 1
    try:
        client.post_catalogue_batches(items)
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
    return parser
