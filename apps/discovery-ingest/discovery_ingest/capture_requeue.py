"""``capture requeue``: queue ``capture_screenshot`` for each categorised page that has no screenshot yet."""

from __future__ import annotations

import argparse
from collections.abc import Iterator, Sequence
from itertools import islice
from typing import Any
from uuid import UUID

from discovery_ingest.api_client import DiscoveryMachineClient
from discovery_ingest.candidate_sources import CandidateSourceRead
from discovery_ingest.cli_errors import failing_with_api_error
from discovery_ingest.config import load_ingest_settings
from discovery_ingest.requeue_common import Counts, add_requeue_options, enqueue_counted
from discovery_ingest.worker.capture_enqueue import capture_request

PAGE_SIZE = 100
"""The most the sources route serves in one page."""
MAX_SERVICE_IDS = 20
"""The most procedures one run may name; the route refuses more."""


class _ServiceIds(argparse.Action):
    """Collect ``--service-id`` values, refusing the twenty-first before any call."""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        """Append the parsed id to the ones given so far."""
        chosen = [*(getattr(namespace, self.dest) or []), values]
        if len(chosen) > MAX_SERVICE_IDS:
            parser.error(f"--service-id may be given at most {MAX_SERVICE_IDS} times")
        setattr(namespace, self.dest, chosen)


def register_capture_parser(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Add the ``capture`` command with its ``requeue`` subcommand."""
    capture = sub.add_parser("capture", help="Screenshots of the pages candidates were found on")
    capture_sub = capture.add_subparsers(dest="capture_command")
    requeue = capture_sub.add_parser("requeue", help="Queue capture_screenshot for categorised pages without one")
    add_requeue_options(requeue)
    requeue.add_argument(
        "--service-id",
        type=UUID,
        action=_ServiceIds,
        default=None,
        help=f"Only this procedure (catalogue row UUID; repeatable, at most {MAX_SERVICE_IDS})",
    )


def _sources(client: DiscoveryMachineClient, args: argparse.Namespace) -> Iterator[CandidateSourceRead]:
    """Yield the pages without a screenshot, busiest first, one route page at a time."""
    offset = 0
    while True:
        page = client.list_candidate_sources(
            host=args.host,
            missing="screenshot",
            candidate_id=None,
            service_ids=args.service_id or [],
            offset=offset,
            limit=min(PAGE_SIZE, args.limit - offset),
        )
        yield from page.items
        offset += len(page.items)
        if not page.items or offset >= min(page.total, args.limit):
            return


def _enqueue_all(client: DiscoveryMachineClient, sources: list[CandidateSourceRead]) -> Counts:
    counts = Counts(pages=len(sources))
    for source in sources:
        enqueue_counted(client, capture_request(source.catalogue_service_id, source.source_url), counts)
    return counts


def _report(counts: Counts, *, dry_run: bool) -> str:
    fields = [f"pages={counts.pages}", f"queued={counts.queued}"]
    fields += [f"already_queued={counts.already_queued}", f"failed={counts.failed}"]
    return " ".join([*fields, "dry_run=true"] if dry_run else fields)


def _requeue(args: argparse.Namespace) -> int:
    settings = load_ingest_settings()
    client = DiscoveryMachineClient(settings.discovery_api_url, settings.discovery_api_key)
    sources = list(islice(_sources(client, args), args.limit))
    counts = Counts(pages=len(sources)) if args.dry_run else _enqueue_all(client, sources)
    print(_report(counts, dry_run=args.dry_run))
    return 1 if counts.failed else 0


capture_requeue = failing_with_api_error("capture requeue", _requeue)
