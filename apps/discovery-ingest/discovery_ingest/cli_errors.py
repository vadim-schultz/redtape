"""Shared exit handling for command line wrappers over the machine API."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

from discovery_ingest.api_client import DiscoveryMachineApiError

Command = Callable[[argparse.Namespace], int]


def failing_with_api_error(label: str, command: Command) -> Command:
    """Turn an API refusal (a bad key, an unknown id) into exit 1 with ``label`` and the API message on stderr."""

    def run(args: argparse.Namespace) -> int:
        try:
            return command(args)
        except DiscoveryMachineApiError as err:
            print(f"{label} command failed: {err}", file=sys.stderr)
            return 1

    return run
