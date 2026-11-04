"""The root Typer app: one sub-app per command group, in the order the operator docs list them."""

import sys

import typer
from typer.main import get_command

from discovery_ingest.cli.artifacts import artifacts_app
from discovery_ingest.cli.browser import browser_app
from discovery_ingest.cli.budget import budget_app
from discovery_ingest.cli.candidates import candidates_app
from discovery_ingest.cli.capture import capture_app
from discovery_ingest.cli.context import CliContext
from discovery_ingest.cli.errors import HELP_OPTIONS, show_help_without_subcommand
from discovery_ingest.cli.fim import fim_app
from discovery_ingest.cli.govdata import govdata_app
from discovery_ingest.cli.leika import leika_app
from discovery_ingest.cli.llm import llm_app
from discovery_ingest.cli.pvog import pvog_app
from discovery_ingest.cli.worker import worker_app

PROG_NAME = "discovery_ingest"

app = typer.Typer(
    name=PROG_NAME,
    help="Discovery catalogue ingest: catalogue imports, enrichment, the worker, curation, probes and the budget ledger.",
    add_completion=False,
    pretty_exceptions_enable=False,
    rich_markup_mode=None,
    context_settings=HELP_OPTIONS,
)
app.add_typer(govdata_app, name="govdata")
app.add_typer(pvog_app, name="pvog")
app.add_typer(fim_app, name="fim")
app.add_typer(leika_app, name="leika")
app.add_typer(worker_app, name="worker")
app.add_typer(candidates_app, name="candidates")
app.add_typer(budget_app, name="budget")
app.add_typer(browser_app, name="browser")
app.add_typer(llm_app, name="llm")
app.add_typer(artifacts_app, name="artifacts")
app.add_typer(capture_app, name="capture")


@app.callback(invoke_without_command=True)
def root(ctx: typer.Context) -> None:
    """Discovery catalogue ingest: catalogue imports, enrichment, the worker, curation, probes and the budget ledger."""
    state = CliContext()
    ctx.obj = state
    ctx.call_on_close(state.close)
    show_help_without_subcommand(ctx)


def _exit_code(code: object) -> int:
    """Map what ``sys.exit`` was given to an integer exit code."""
    if code is None:
        return 0
    if isinstance(code, int):
        return code
    print(code, file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    """Run the command line on ``argv`` (``sys.argv[1:]`` when ``None``) and return the exit code.

    Usage errors and ``--help`` leave through click's ``SystemExit``; it is caught here, so callers get a code.
    """
    command = get_command(app)
    try:
        command.main(args=argv, prog_name=PROG_NAME, standalone_mode=True)
    except SystemExit as err:
        return _exit_code(err.code)
    return 0
