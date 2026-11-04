"""Rendering shared by several commands. Machine-read output is written with ``typer.echo``, never with rich."""

from __future__ import annotations

import typer


def echo_skip(message: str) -> None:
    """Report a catalogue row that was skipped, on stderr."""
    typer.echo(f"skip row: {message}", err=True)
