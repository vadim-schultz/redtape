"""``llm requeue``: queue ``llm_extract`` for the latest snapshot of each catalogue row, for the backlog and for bumps."""

from __future__ import annotations

import argparse
import sys

from discovery_ingest.artifacts import ArtifactRead
from discovery_ingest.cli_errors import failing_with_api_error
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.config import load_ingest_settings
from discovery_ingest.latest_snapshots import latest_snapshots
from discovery_ingest.requeue_common import Counts, add_requeue_options, enqueue_counted
from discovery_ingest.worker.llm_enqueue import llm_extract_request, llm_input_key

EXIT_MISSING_MODEL = 2


def register_requeue_parser(llm_sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Add ``requeue`` to the ``llm`` command."""
    requeue = llm_sub.add_parser("requeue", help="Queue llm_extract for the latest snapshots under the current key")
    add_requeue_options(requeue)


def enqueue_all(client: DiscoveryIngestClient, snapshots: list[ArtifactRead], model: str) -> Counts:
    """Enqueue ``llm_extract`` for each snapshot; the queue's identity answers ``created`` false for a known key."""
    counts = Counts(pages=len(snapshots))
    for artifact in snapshots:
        enqueue_counted(client, llm_extract_request(artifact, model), counts)
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
    with DiscoveryIngestClient.from_settings(settings) as client:
        snapshots = latest_snapshots(client, args.host, args.limit)
        counts = Counts(pages=len(snapshots)) if args.dry_run else enqueue_all(client, snapshots, settings.llm_model)
    print(_report(settings.llm_model, counts, dry_run=args.dry_run))
    return 1 if counts.failed else 0


llm_requeue = failing_with_api_error("llm requeue", _requeue)
