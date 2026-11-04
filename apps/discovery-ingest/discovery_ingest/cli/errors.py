"""Exit codes, and the one place that turns a failure into a message on stderr and an exit code."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import NoReturn, ParamSpec, TypeVar

import typer

from discovery_ingest.client import DiscoveryMachineApiError

EXIT_FAILED = 1
EXIT_USAGE = 2
HELP_OPTIONS: dict[str, object] = {"help_option_names": ["-h", "--help"], "max_content_width": 120}
"""``-h`` and ``--help`` at every level, as argparse had them; wide help so long defaults do not split words."""

P = ParamSpec("P")
R = TypeVar("R")


def fail(message: str, code: int = EXIT_FAILED) -> NoReturn:
    """Print ``message`` on stderr and exit with ``code``."""
    typer.echo(message, err=True)
    raise typer.Exit(code)


def handles_api_errors(label: str | None) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Turn an API refusal into exit 1 with ``{label} command failed: {err}`` on stderr.

    With no label the refusal's own message is printed, as ``govdata fetch`` always did.
    """

    def decorate(command: Callable[P, R]) -> Callable[P, R]:
        @wraps(command)
        def run(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return command(*args, **kwargs)
            except DiscoveryMachineApiError as err:
                fail(f"{label} command failed: {err}" if label else str(err))

        return run

    return decorate


def show_help_without_subcommand(ctx: typer.Context) -> None:
    """Print the help of a group that was run without a subcommand, and exit 2."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(EXIT_USAGE)
