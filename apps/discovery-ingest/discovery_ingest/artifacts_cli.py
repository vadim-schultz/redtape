"""``artifacts list`` and ``artifacts download``: bring stored page snapshots to a developer as fixtures."""

from __future__ import annotations

import argparse
from collections.abc import Iterator
from pathlib import Path
from typing import get_args
from uuid import UUID

from discovery_ingest.api_client import DiscoveryMachineClient
from discovery_ingest.artifacts import ArtifactKind, ArtifactRead
from discovery_ingest.cli_errors import failing_with_api_error
from discovery_ingest.config import load_ingest_settings

MAX_PAGE_SIZE = 100


def _positive_int(raw: str) -> int:
    if not raw.isdigit() or int(raw) < 1:
        raise argparse.ArgumentTypeError(f"expected a positive whole number; got {raw!r}")
    return int(raw)


def register_artifacts_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Add the ``artifacts`` command with its ``list`` and ``download`` subcommands."""
    artifacts = sub.add_parser("artifacts", help="Stored page snapshots and screenshots")
    artifacts_sub = artifacts.add_subparsers(dest="artifacts_command")
    listing = artifacts_sub.add_parser("list", help="Print id, kind, size and source url of stored artifacts of a host")
    listing.add_argument("--host", required=True, help="Source host, for example verwaltung.bund.de")
    listing.add_argument("--limit", type=_positive_int, default=20, help="Maximum artifacts to print (default 20)")
    listing.add_argument("--kind", choices=get_args(ArtifactKind), default="html_snapshot")
    download = artifacts_sub.add_parser("download", help="Write the stored bytes of one artifact to a file")
    download.add_argument("--id", type=UUID, required=True, help="Artifact id from `artifacts list`")
    download.add_argument("--out", type=Path, required=True, help="File to write; parent directories are created")


def _client() -> DiscoveryMachineClient:
    settings = load_ingest_settings()
    return DiscoveryMachineClient(settings.discovery_api_url, settings.discovery_api_key)


def _artifacts(client: DiscoveryMachineClient, args: argparse.Namespace) -> Iterator[ArtifactRead]:
    """Yield up to ``args.limit`` artifacts, one route page at a time, newest first."""
    offset = 0
    while offset < args.limit:
        page = client.list_artifacts(
            host=args.host, kind=args.kind, offset=offset, limit=min(MAX_PAGE_SIZE, args.limit - offset)
        )
        yield from page.items
        offset += len(page.items)
        if not page.items or offset >= page.total:
            return


def _line(artifact: ArtifactRead) -> str:
    return "\t".join([str(artifact.id), artifact.kind, str(artifact.byte_size), artifact.source_url])


def _list(args: argparse.Namespace) -> int:
    for artifact in _artifacts(_client(), args):
        print(_line(artifact))
    return 0


def _download(args: argparse.Namespace) -> int:
    content = _client().get_artifact_content(args.id)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(content.data)
    print(f"wrote {args.out} ({len(content.data)} bytes)")
    return 0


artifacts_list = failing_with_api_error("artifacts", _list)
artifacts_download = failing_with_api_error("artifacts", _download)
