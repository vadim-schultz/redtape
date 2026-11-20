"""``catalogue``: weekly upkeep of the catalogue rows the pipeline already holds."""

from typing import Annotated

import typer

from discovery_ingest.cli.context import api_client
from discovery_ingest.cli.errors import EXIT_FAILED, HELP_OPTIONS, handles_api_errors, show_help_without_subcommand
from discovery_ingest.operations.catalogue_refresh import (
    DEFAULT_GOVDATA_MAX_PAGES,
    DEFAULT_PVOG_MAX_PAGES,
    refresh_bound,
    refresh_stale_fetches,
)
from discovery_ingest.operations.requeue import Counts

catalogue_app = typer.Typer(
    name="catalogue",
    help="Weekly upkeep of the catalogue rows",
    add_completion=False,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
    context_settings=HELP_OPTIONS,
)


@catalogue_app.callback(invoke_without_command=True)
def catalogue_group(ctx: typer.Context) -> None:
    """Weekly upkeep of the catalogue rows."""
    show_help_without_subcommand(ctx)


def _report(bound: int, counts: Counts) -> str:
    """Return the one-line summary: the bound used, then the pages read and how each enqueue answered."""
    fields = [f"bound={bound}", f"pages={counts.pages}", f"queued={counts.queued}"]
    return " ".join([*fields, f"already_queued={counts.already_queued}", f"failed={counts.failed}"])


@catalogue_app.command("refresh")
@handles_api_errors("catalogue refresh")
def catalogue_refresh_command(
    ctx: typer.Context,
    max_rows: Annotated[
        int,
        typer.Option("--max-rows", help="Stale pages to re-fetch this run; 0, the default, turns the refresh off"),
    ] = 0,
    govdata_max_pages: Annotated[
        int,
        typer.Option("--govdata-max-pages", help="The GovData page cap of the weekly run; the bound stays under it"),
    ] = DEFAULT_GOVDATA_MAX_PAGES,
    pvog_max_pages: Annotated[
        int,
        typer.Option("--pvog-max-pages", help="The PVOG page cap of the weekly run; the bound stays under it"),
    ] = DEFAULT_PVOG_MAX_PAGES,
) -> None:
    """Re-enqueue stale portal pages for a bounded weekly refresh."""
    caps = (govdata_max_pages, pvog_max_pages)
    counts = refresh_stale_fetches(api_client(ctx), max_rows=max_rows, page_caps=caps)
    typer.echo(_report(refresh_bound(max_rows, page_caps=caps), counts))
    if counts.failed:
        raise typer.Exit(EXIT_FAILED)
