"""``capture``: screenshots of the pages candidates were found on."""

from typing import Annotated
from uuid import UUID

import typer

from discovery_ingest.cli.context import api_client
from discovery_ingest.cli.errors import EXIT_FAILED, HELP_OPTIONS, handles_api_errors, show_help_without_subcommand
from discovery_ingest.cli.options import RequeueDryRun, RequeueHost, RequeueLimit
from discovery_ingest.operations.requeue import DEFAULT_LIMIT, MAX_SERVICE_IDS, Counts, capture_requeue

capture_app = typer.Typer(
    name="capture",
    help="Screenshots of the pages candidates were found on",
    add_completion=False,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
    context_settings=HELP_OPTIONS,
)


@capture_app.callback(invoke_without_command=True)
def capture_group(ctx: typer.Context) -> None:
    """Screenshots of the pages candidates were found on."""
    show_help_without_subcommand(ctx)


def _report(counts: Counts, *, dry_run: bool) -> str:
    fields = [f"pages={counts.pages}", f"queued={counts.queued}"]
    fields += [f"already_queued={counts.already_queued}", f"failed={counts.failed}"]
    return " ".join([*fields, "dry_run=true"] if dry_run else fields)


@capture_app.command("requeue")
@handles_api_errors("capture requeue")
def capture_requeue_command(
    ctx: typer.Context,
    host: RequeueHost = None,
    limit: RequeueLimit = DEFAULT_LIMIT,
    dry_run: RequeueDryRun = False,
    service_id: Annotated[
        list[UUID] | None,
        typer.Option(
            "--service-id",
            help=f"Only this procedure (catalogue row UUID; repeatable, at most {MAX_SERVICE_IDS})",
        ),
    ] = None,
) -> None:
    """Queue capture_screenshot for categorised pages without one."""
    chosen = service_id or []
    if len(chosen) > MAX_SERVICE_IDS:
        raise typer.BadParameter(
            f"--service-id may be given at most {MAX_SERVICE_IDS} times", param_hint="--service-id"
        )
    counts = capture_requeue(api_client(ctx), host=host, limit=limit, service_ids=chosen, dry_run=dry_run)
    typer.echo(_report(counts, dry_run=dry_run))
    if counts.failed:
        raise typer.Exit(EXIT_FAILED)
