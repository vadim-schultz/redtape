"""``govdata``: the GovData OZG catalogue ingest."""

from pathlib import Path
from typing import Annotated
from uuid import UUID

import typer

from discovery_ingest.cli.context import api_client, settings_of
from discovery_ingest.cli.errors import HELP_OPTIONS, fail, handles_api_errors, show_help_without_subcommand
from discovery_ingest.cli.render import echo_skip
from discovery_ingest.govdata.ckan import GovDataCkanClient, GovDataCkanError
from discovery_ingest.operations.catalogue import GovDataCkanSource, GovDataFileSource, NothingToIngest, ingest

JURISDICTION_HELP = "Jurisdiction UUID for federal rows (ars 000000000000)"

govdata_app = typer.Typer(
    name="govdata",
    help="GovData OZG catalogue ingest",
    add_completion=False,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
    context_settings=HELP_OPTIONS,
)


@govdata_app.callback(invoke_without_command=True)
def govdata_group(ctx: typer.Context) -> None:
    """GovData OZG catalogue ingest."""
    show_help_without_subcommand(ctx)


@govdata_app.command("run")
@handles_api_errors("govdata")
def govdata_run(
    ctx: typer.Context,
    input_path: Annotated[str, typer.Option("--input", help="Path to OZG Leistungen JSON page")],
    jurisdiction_id: Annotated[UUID, typer.Option("--jurisdiction-id", help=JURISDICTION_HELP)],
) -> None:
    """Upsert rows from a Leistungen JSON export."""
    source = GovDataFileSource(Path(input_path), jurisdiction_id)
    try:
        ingest(source, api_client(ctx), on_skip=echo_skip)
    except NothingToIngest as err:
        fail(str(err))


@govdata_app.command("fetch")
@handles_api_errors(None)
def govdata_fetch(
    ctx: typer.Context,
    jurisdiction_id: Annotated[UUID, typer.Option("--jurisdiction-id", help=JURISDICTION_HELP)],
    max_pages: Annotated[
        int, typer.Option("--max-pages", help="Maximum Leistungen feed pages per run (default 150)")
    ] = 150,
    page_size: Annotated[int, typer.Option("--page-size", help="Rows per Leistungen feed page (default 100)")] = 100,
    max_records: Annotated[
        int | None, typer.Option("--max-records", help="Optional safety cap on total rows fetched")
    ] = None,
) -> None:
    """Fetch OZG Leistungen from GovData CKAN and upsert."""
    settings = settings_of(ctx)
    ckan = GovDataCkanClient(
        settings.govdata_ckan_base_url,
        settings.govdata_package_id,
        scope_ars=settings.govdata_open_pvog_ars,
    )
    source = GovDataCkanSource(
        ckan,
        jurisdiction_id,
        max_pages=max_pages,
        page_size=page_size,
        max_records=max_records,
    )
    try:
        ingest(source, api_client(ctx), on_skip=echo_skip)
    except GovDataCkanError as err:
        fail(f"govdata fetch failed: {err}")
    except NothingToIngest as err:
        fail(str(err))
