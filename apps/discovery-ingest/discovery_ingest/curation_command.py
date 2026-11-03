"""``candidates curate``: validate a curation file, plan it and post it through the machine routes (chapter 11)."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from discovery_ingest.candidate_sources import CandidateSourceRead
from discovery_ingest.cli_errors import failing_with_api_error
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.config import load_ingest_settings
from discovery_ingest.curation import CurationFile
from discovery_ingest.curation_check import code_problems, grounding_problems, title_problems
from discovery_ingest.curation_load import CurationError, load_curation_file
from discovery_ingest.curation_pages import PageTexts, candidate_procedures
from discovery_ingest.curation_plan import CurationPlan, plan_curation
from discovery_ingest.curation_run import Totals, post_plan
from discovery_ingest.curation_staged import StagedIndex

EXIT_REFUSED = 2
NOT_CHECKED = "warning: --no-check-pages: excerpts were not compared with the page text"
TOTAL_FIELDS = (
    "mentions_created",
    "mentions_updated",
    "edges_created",
    "edges_updated",
    "edges_skipped",
    "unknown_codes",
)
Stage = Callable[[], list[str]]


@dataclass(frozen=True, slots=True)
class Reads:
    """What the file is checked against: the staged candidates and the procedures of each entry's candidate."""

    staged: StagedIndex
    procedures: dict[UUID, list[CandidateSourceRead]]


def _read(client: DiscoveryIngestClient, file: CurationFile) -> Reads:
    procedures = {c.candidate_id: candidate_procedures(client, c.candidate_id) for c in file.candidates}
    return Reads(StagedIndex.fetch(client), procedures)


def _stages(client: DiscoveryIngestClient, file: CurationFile, reads: Reads, *, check_pages: bool) -> list[Stage]:
    stages: list[Stage] = [
        lambda: code_problems(file, client.candidates.taxonomy()),
        lambda: title_problems(file, reads.staged, reads.procedures),
    ]
    if check_pages:
        stages.append(lambda: grounding_problems(file, reads.procedures, PageTexts(client)))
    return stages


def _first_problems(stages: list[Stage]) -> list[str]:
    """Run the stages in order and return the first one's problems, so a typo costs no page downloads."""
    return next((found for stage in stages if (found := stage())), [])


def _totals_line(totals: Totals, *, dry_run: bool) -> str:
    counts = [f"{name}={getattr(totals, name)}" for name in TOTAL_FIELDS]
    return " ".join([*counts, f"dry_run={str(dry_run).lower()}"])


def _report(plan: CurationPlan, totals: Totals, *, dry_run: bool) -> None:
    print("\n".join(f"{line.title} tags={line.tags} edges={line.edges}" for line in plan.lines))
    print(_totals_line(totals, dry_run=dry_run))
    for skipped in totals.skipped:
        print(f"edge skipped {skipped}", file=sys.stderr)


def _refuse(problems: list[str]) -> int:
    print("\n".join(f"curation refused: {problem}" for problem in problems), file=sys.stderr)
    return EXIT_REFUSED


def _execute(client: DiscoveryIngestClient, plan: CurationPlan, *, dry_run: bool) -> int:
    totals = Totals() if dry_run else post_plan(client, plan)
    _report(plan, totals, dry_run=dry_run)
    return 1 if totals.refused else 0


def _apply(client: DiscoveryIngestClient, file: CurationFile, args: argparse.Namespace) -> int:
    reads = _read(client, file)
    if problems := _first_problems(_stages(client, file, reads, check_pages=args.check_pages)):
        return _refuse(problems)
    if not args.check_pages:
        print(NOT_CHECKED, file=sys.stderr)
    return _execute(client, plan_curation(file, reads.staged), dry_run=args.dry_run)


def _curate(args: argparse.Namespace) -> int:
    try:
        file = load_curation_file(Path(args.file))
    except CurationError as err:
        return _refuse(err.problems)
    with DiscoveryIngestClient.from_settings(load_ingest_settings()) as client:
        return _apply(client, file, args)


candidates_curate = failing_with_api_error("candidates curate", _curate)
