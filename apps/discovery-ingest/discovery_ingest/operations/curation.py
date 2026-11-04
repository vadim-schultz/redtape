"""``candidates curate``: check a curation file against the staged candidates and the pages, then post its plan."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from discovery_ingest.candidate_sources import CandidateSourceRead
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.curation import CurationFile
from discovery_ingest.curation_check import code_problems, grounding_problems, title_problems
from discovery_ingest.curation_pages import PageTexts, candidate_procedures
from discovery_ingest.curation_plan import CurationPlan, plan_curation
from discovery_ingest.curation_run import Totals, post_plan
from discovery_ingest.curation_staged import StagedIndex

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


def check_curation(client: DiscoveryIngestClient, file: CurationFile, *, check_pages: bool) -> tuple[Reads, list[str]]:
    """Read what the file refers to and return it with the problems of its first failing check (none when it passes)."""
    reads = _read(client, file)
    return reads, _first_problems(_stages(client, file, reads, check_pages=check_pages))


def run_curation(
    client: DiscoveryIngestClient, file: CurationFile, reads: Reads, *, dry_run: bool
) -> tuple[CurationPlan, Totals]:
    """Plan the checked file and post the plan, or only count its effect when ``dry_run``; return the plan and totals."""
    plan = plan_curation(file, reads.staged)
    totals = Totals() if dry_run else post_plan(client, plan)
    return plan, totals
