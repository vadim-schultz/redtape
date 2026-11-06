"""``candidates``: emit staged candidates, read a candidate's pages, and curate by hand (chapter 11)."""

from pathlib import Path
from typing import Annotated, NoReturn
from uuid import UUID

import typer

from discovery_ingest.candidate_emit import DEFAULT_EMIT_LIMIT, EmitSelection, emit_report, preview_report
from discovery_ingest.candidate_sources import CandidateSourceRead
from discovery_ingest.cli.context import api_client
from discovery_ingest.cli.errors import (
    EXIT_FAILED,
    EXIT_USAGE,
    HELP_OPTIONS,
    fail,
    handles_api_errors,
    show_help_without_subcommand,
)
from discovery_ingest.client import DiscoveryMachineApiError
from discovery_ingest.curation_load import CurationError, load_curation_file
from discovery_ingest.curation_pages import candidate_procedures
from discovery_ingest.curation_run import Totals
from discovery_ingest.operations.candidate_pages import write_cleaned_texts
from discovery_ingest.operations.curation import check_curation, run_curation

NOT_CHECKED = "warning: --no-check-pages: excerpts were not compared with the page text"
TOTAL_FIELDS = (
    "mentions_created",
    "mentions_updated",
    "edges_created",
    "edges_updated",
    "edges_skipped",
    "unknown_codes",
)
REVERSAL = """\
\b
There is no machine delete. To undo a curation, run as the database owner, in this order:
  DELETE FROM discovery_candidate_edge WHERE extractor = 'manual';
  DELETE FROM discovery_candidate_mention WHERE extractor = 'manual';
  DELETE FROM discovery_document_candidate c WHERE c.status = 'staged'
    AND NOT EXISTS (SELECT 1 FROM discovery_candidate_mention m WHERE m.candidate_id = c.id);
"""

candidates_app = typer.Typer(
    name="candidates",
    help="Document candidates",
    add_completion=False,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
    context_settings=HELP_OPTIONS,
)


@candidates_app.callback(invoke_without_command=True)
def candidates_group(ctx: typer.Context) -> None:
    """Document candidates."""
    show_help_without_subcommand(ctx)


@candidates_app.command("emit")
def candidates_emit(
    ctx: typer.Context,
    ids: Annotated[list[UUID] | None, typer.Option("--id", help="Candidate to emit (repeatable)")] = None,
    all_staged: Annotated[bool, typer.Option("--all-staged", help="Emit the most mentioned staged candidates")] = False,
    min_mentions: Annotated[
        int, typer.Option("--min-mentions", help="With --all-staged: minimum mentions (default 0)")
    ] = 0,
    limit: Annotated[
        int,
        typer.Option("--limit", help=f"Maximum candidates to emit (1-50, default {DEFAULT_EMIT_LIMIT})"),
    ] = DEFAULT_EMIT_LIMIT,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview only; nothing is written")] = False,
) -> None:
    """Emit staged candidates as pending suggestions."""
    if bool(ids) == all_staged:
        raise typer.BadParameter("give either --id (repeatable) or --all-staged, not both or neither")
    selection = EmitSelection(tuple(ids or ()), min_mentions, limit)
    try:
        selection.validate()
    except ValueError as err:
        fail(f"invalid selection: {err}", EXIT_USAGE)
    report = preview_report if dry_run else emit_report
    try:
        lines = report(api_client(ctx), selection)
    except DiscoveryMachineApiError as err:
        fail(f"emit failed: {err}")
    typer.echo("\n".join(lines))


def _page_line(source: CandidateSourceRead) -> str:
    flag = f"has_screenshot={str(source.has_screenshot).lower()}"
    return " ".join([str(source.catalogue_service_id), source.source_url, source.host, flag])


@candidates_app.command("page")
@handles_api_errors("candidates page")
def candidates_page(
    ctx: typer.Context,
    candidate_id: Annotated[UUID, typer.Option("--candidate-id")],
    out: Annotated[
        Path | None,
        typer.Option("--out", help="Directory for <catalogue_service_id>.txt files"),
    ] = None,
) -> None:
    """Print the procedures of a candidate; --out writes their cleaned text."""
    client = api_client(ctx)
    sources = candidate_procedures(client, candidate_id)
    if not sources:
        fail(f"no procedures for {candidate_id}")
    typer.echo("\n".join(_page_line(source) for source in sources))
    if out is None:
        return
    missing = write_cleaned_texts(client, sources, out)
    for service_id in missing:
        typer.echo(f"no html_snapshot for {service_id}", err=True)
    if missing:
        raise typer.Exit(EXIT_FAILED)


def _refuse(problems: list[str]) -> NoReturn:
    typer.echo("\n".join(f"curation refused: {problem}" for problem in problems), err=True)
    raise typer.Exit(EXIT_USAGE)


def _totals_line(totals: Totals, *, dry_run: bool) -> str:
    counts = [f"{name}={getattr(totals, name)}" for name in TOTAL_FIELDS]
    return " ".join([*counts, f"dry_run={str(dry_run).lower()}"])


def _report(plan_lines: list[str], totals: Totals, *, dry_run: bool) -> None:
    typer.echo("\n".join(plan_lines))
    typer.echo(_totals_line(totals, dry_run=dry_run))
    for skipped in totals.skipped:
        typer.echo(f"edge skipped {skipped}", err=True)


@candidates_app.command("curate", epilog=REVERSAL)
@handles_api_errors("candidates curate")
def candidates_curate(
    ctx: typer.Context,
    file_path: Annotated[str, typer.Option("--file", help="JSON curation file (at most 8 candidates and 60 edges)")],
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Validate and plan; make no write call")] = False,
    check_pages: Annotated[
        bool,
        typer.Option(
            "--check-pages/--no-check-pages",
            help="Require every excerpt to be on the cleaned page text (default on)",
        ),
    ] = True,
) -> None:
    """Apply a reviewed curation file as manual tags and edges."""
    client = api_client(ctx)
    try:
        file = load_curation_file(Path(file_path))
    except CurationError as err:
        _refuse(err.problems)
    reads, problems = check_curation(client, file, check_pages=check_pages)
    if problems:
        _refuse(problems)
    if not check_pages:
        typer.echo(NOT_CHECKED, err=True)
    plan, totals = run_curation(client, file, reads, dry_run=dry_run)
    _report([f"{line.title} tags={line.tags} edges={line.edges}" for line in plan.lines], totals, dry_run=dry_run)
    if totals.refused:
        raise typer.Exit(EXIT_FAILED)
