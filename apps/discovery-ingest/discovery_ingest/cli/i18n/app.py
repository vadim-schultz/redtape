"""The ``i18n`` command group: its Typer app and the help it prints without a subcommand."""

import typer

from discovery_ingest.cli.errors import HELP_OPTIONS, show_help_without_subcommand

i18n_app = typer.Typer(
    name="i18n",
    help="Interface-string translation",
    add_completion=False,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
    context_settings=HELP_OPTIONS,
)


@i18n_app.callback(invoke_without_command=True)
def i18n_group(ctx: typer.Context) -> None:
    """Interface-string translation."""
    show_help_without_subcommand(ctx)
