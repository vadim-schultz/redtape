"""What ``llm requeue`` and ``capture requeue`` share: the page limit, the counts and the counted enqueue."""

from __future__ import annotations

import argparse
from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from discovery_ingest.client import DiscoveryIngestClient, DiscoveryMachineApiError
from discovery_ingest.schemas import TaskEnqueueRequest

DEFAULT_LIMIT = 50
MAX_LIMIT = 200
"""More pages than this in one run would commit more neurons or browser seconds than a day allows; refused before any call."""


@dataclass(slots=True)
class Counts:
    """What a requeue did, one count per page: queued now, already queued under this key, or refused."""

    pages: int = 0
    queued: int = 0
    already_queued: int = 0
    failed: int = 0


def limit_arg(raw: str) -> int:
    """Parse ``--limit``: a whole number from 1 to :data:`MAX_LIMIT`."""
    if not raw.isdigit() or not 1 <= int(raw) <= MAX_LIMIT:
        raise argparse.ArgumentTypeError(f"expected a whole number from 1 to {MAX_LIMIT}; got {raw!r}")
    return int(raw)


def add_requeue_options(parser: argparse.ArgumentParser) -> None:
    """Add ``--host``, ``--limit`` and ``--dry-run``, the options both requeue commands take."""
    parser.add_argument("--host", default=None, help="Only pages of this source host (default: every host)")
    parser.add_argument(
        "--limit",
        type=limit_arg,
        default=DEFAULT_LIMIT,
        help=f"Maximum pages to queue (1-{MAX_LIMIT}, default {DEFAULT_LIMIT})",
    )
    parser.add_argument("--dry-run", action="store_true", help="Count the pages; make no enqueue call")


def enqueue_counted(client: DiscoveryIngestClient, request: TaskEnqueueRequest, counts: Counts) -> None:
    """Enqueue ``request`` and count the answer; the queue's identity answers ``created`` false for a known key."""
    try:
        created = client.tasks.enqueue(request).created
    except (DiscoveryMachineApiError, httpx.HTTPError, ValidationError):
        counts.failed += 1
        return
    counts.queued += created
    counts.already_queued += not created
