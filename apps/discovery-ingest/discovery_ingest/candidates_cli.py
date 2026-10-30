"""``candidates page`` and ``candidates curate``: read a candidate's source pages, then complete it by hand (chapter 11)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from uuid import UUID

from discovery_ingest.api_client import DiscoveryMachineClient
from discovery_ingest.candidate_sources import CandidateSourceRead
from discovery_ingest.cli_errors import failing_with_api_error
from discovery_ingest.curation_pages import candidate_procedures, cleaned_text
from discovery_ingest.machine_client import machine_client

REVERSAL = """\
There is no machine delete. To undo a curation, run as the database owner, in this order:
  DELETE FROM discovery_candidate_edge WHERE extractor = 'manual';
  DELETE FROM discovery_candidate_mention WHERE extractor = 'manual';
  DELETE FROM discovery_document_candidate c WHERE c.status = 'staged'
    AND NOT EXISTS (SELECT 1 FROM discovery_candidate_mention m WHERE m.candidate_id = c.id);
"""


def register_candidates_aids(candidates_sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Add ``page`` and ``curate`` to the ``candidates`` command."""
    page = candidates_sub.add_parser(
        "page", help="Print the procedures of a candidate; --out writes their cleaned text"
    )
    page.add_argument("--candidate-id", type=UUID, required=True)
    page.add_argument("--out", type=Path, default=None, help="Directory for <catalogue_service_id>.txt files")
    curate = candidates_sub.add_parser(
        "curate",
        help="Apply a reviewed curation file as manual tags and edges",
        epilog=REVERSAL,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    curate.add_argument("--file", required=True, help="JSON curation file (at most 8 candidates and 60 edges)")
    curate.add_argument("--dry-run", action="store_true", help="Validate and plan; make no write call")
    curate.add_argument(
        "--check-pages",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Require every excerpt to be on the cleaned page text (default on)",
    )


def _line(source: CandidateSourceRead) -> str:
    flag = f"has_screenshot={str(source.has_screenshot).lower()}"
    return " ".join([str(source.catalogue_service_id), source.source_url, source.host, flag])


def _write_text(client: DiscoveryMachineClient, source: CandidateSourceRead, out: Path) -> bool:
    text = cleaned_text(client, source)
    if text is None:
        print(f"no html_snapshot for {source.catalogue_service_id}", file=sys.stderr)
        return False
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{source.catalogue_service_id}.txt").write_text(text, encoding="utf-8")
    return True


def _write_all(client: DiscoveryMachineClient, sources: list[CandidateSourceRead], out: Path | None) -> int:
    """Write the cleaned text of every procedure when ``out`` is given; the exit code is 1 if any snapshot is missing."""
    written = [out is None or _write_text(client, source, out) for source in sources]
    return 0 if all(written) else 1


def _page(args: argparse.Namespace) -> int:
    client = machine_client()
    sources = candidate_procedures(client, args.candidate_id)
    if not sources:
        print(f"no procedures for {args.candidate_id}", file=sys.stderr)
        return 1
    print("\n".join(_line(source) for source in sources))
    return _write_all(client, sources, args.out)


candidates_page = failing_with_api_error("candidates page", _page)
