"""The ``discovery_ingest`` command line: a Typer app with one sub-app per command group.

``main(argv)`` returns the exit code; ``python -m discovery_ingest`` is the supported entry point.
"""

from discovery_ingest.cli.main import app, main

__all__ = ["app", "main"]
