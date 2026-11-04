"""``pvog``: the PVOG Suchdienst catalogue ingest."""

from typing import Annotated
from uuid import UUID

import typer

from discovery_ingest.catalogue_scope import FEDERAL_ARS
from discovery_ingest.cli.context import api_client, settings_of
from discovery_ingest.cli.errors import HELP_OPTIONS, fail, handles_api_errors, show_help_without_subcommand
from discovery_ingest.cli.render import echo_skip
from discovery_ingest.operations.catalogue import NothingToIngest, PvogSource, ingest
from discovery_ingest.pvog.client import PvogClient, PvogClientError

pvog_app = typer.Typer(
    name="pvog",
    help="PVOG Suchdienst catalogue ingest",
    add_completion=False,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
    context_settings=HELP_OPTIONS,
)


@pvog_app.callback(invoke_without_command=True)
def pvog_group(ctx: typer.Context) -> None:
    """PVOG Suchdienst catalogue ingest."""
    show_help_without_subcommand(ctx)


@pvog_app.command("run")
@handles_api_errors("pvog")
def pvog_run(
    ctx: typer.Context,
    jurisdiction_id: Annotated[
        UUID, typer.Option("--jurisdiction-id", help="Jurisdiction UUID for federal scope (ars 000000000000)")
    ],
    max_pages: Annotated[
        int | None, typer.Option("--max-pages", help="Optional cap on PVOG pagination pages per run")
    ] = None,
) -> None:
    """Upsert rows from PVOG Suchdienst API."""
    settings = settings_of(ctx)
    source = PvogSource(PvogClient(settings.pvog_api_base_url), jurisdiction_id, max_pages=max_pages)
    try:
        ingest(source, api_client(ctx), on_skip=echo_skip)
    except (PvogClientError, NothingToIngest) as err:
        fail(str(err))


@pvog_app.command("vocabulary")
def pvog_vocabulary(ctx: typer.Context) -> None:
    """Print the full personalMatters leaf vocabulary from the v7 bootstrap tree."""
    pvog = PvogClient(settings_of(ctx).pvog_api_base_url)
    try:
        codes = pvog.fetch_personal_matter_vocabulary(ars=FEDERAL_ARS)
    except PvogClientError as err:
        fail(str(err))
    typer.echo("\n".join(codes))
