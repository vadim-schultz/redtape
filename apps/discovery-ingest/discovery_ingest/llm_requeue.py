"""``llm requeue``: queue ``llm_extract`` for the latest snapshot of each catalogue row, for the backlog and for bumps."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from discovery_ingest.api_client import DiscoveryMachineApiError, DiscoveryMachineClient
from discovery_ingest.artifacts import ArtifactRead
from discovery_ingest.cli_errors import failing_with_api_error
from discovery_ingest.config import load_ingest_settings
from discovery_ingest.latest_snapshots import latest_snapshots
from discovery_ingest.worker.llm_enqueue import llm_extract_request, llm_input_key

DEFAULT_LIMIT = 50
MAX_LIMIT = 200
"""More pages than this in one run would commit more neurons than a day allows; the command refuses before any call."""
EXIT_MISSING_MODEL = 2


@dataclass(slots=True)
class Counts:
    """What a requeue did, one count per page: queued now, already queued under this key, or refused."""

    pages: int = 0
    queued: int = 0
    already_queued: int = 0
    failed: int = 0


def _limit_arg(raw: str) -> int:
    if not raw.isdigit() or not 1 <= int(raw) <= MAX_LIMIT:
        raise argparse.ArgumentTypeError(f"expected a whole number from 1 to {MAX_LIMIT}; got {raw!r}")
    return int(raw)


def register_requeue_parser(llm_sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Add ``requeue`` to the ``llm`` command."""
    requeue = llm_sub.add_parser("requeue", help="Queue llm_extract for the latest snapshots under the current key")
    requeue.add_argument("--host", default=None, help="Only snapshots of this source host (default: every host)")
    requeue.add_argument(
        "--limit",
        type=_limit_arg,
        default=DEFAULT_LIMIT,
        help=f"Maximum pages to queue (1-{MAX_LIMIT}, default {DEFAULT_LIMIT})",
    )
    requeue.add_argument("--dry-run", action="store_true", help="Count the pages; make no enqueue call")


def _enqueue(client: DiscoveryMachineClient, artifact: ArtifactRead, model: str, counts: Counts) -> None:
    try:
        created = client.enqueue_task(llm_extract_request(artifact, model)).created
    except (DiscoveryMachineApiError, httpx.HTTPError, ValidationError):
        counts.failed += 1
        return
    counts.queued += created
    counts.already_queued += not created


def enqueue_all(client: DiscoveryMachineClient, snapshots: list[ArtifactRead], model: str) -> Counts:
    """Enqueue ``llm_extract`` for each snapshot; the queue's identity answers ``created`` false for a known key."""
    counts = Counts(pages=len(snapshots))
    for artifact in snapshots:
        _enqueue(client, artifact, model, counts)
    return counts


def _report(model: str, counts: Counts, *, dry_run: bool) -> str:
    fields = [f"key={llm_input_key(model)}", f"pages={counts.pages}", f"queued={counts.queued}"]
    fields += [f"already_queued={counts.already_queued}", f"failed={counts.failed}"]
    return " ".join([*fields, "dry_run=true"] if dry_run else fields)


def _requeue(args: argparse.Namespace) -> int:
    settings = load_ingest_settings()
    if not settings.llm_model:
        print("llm requeue needs the environment variable LLM_MODEL (it keys the task)", file=sys.stderr)
        return EXIT_MISSING_MODEL
    client = DiscoveryMachineClient(settings.discovery_api_url, settings.discovery_api_key)
    snapshots = latest_snapshots(client, args.host, args.limit)
    counts = Counts(pages=len(snapshots)) if args.dry_run else enqueue_all(client, snapshots, settings.llm_model)
    print(_report(settings.llm_model, counts, dry_run=args.dry_run))
    return 1 if counts.failed else 0


llm_requeue = failing_with_api_error("llm requeue", _requeue)
