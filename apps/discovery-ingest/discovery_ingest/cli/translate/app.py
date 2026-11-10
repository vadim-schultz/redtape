"""The ``translate`` command group: its Typer app and the help it prints without a subcommand."""

import typer

from discovery_ingest.cli.errors import HELP_OPTIONS, show_help_without_subcommand

translate_app = typer.Typer(
    name="translate",
    help="Document translation engines",
    add_completion=False,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
    context_settings=HELP_OPTIONS,
)


@translate_app.callback(invoke_without_command=True)
def translate_group(ctx: typer.Context) -> None:
    """Document translation engines."""
    show_help_without_subcommand(ctx)
