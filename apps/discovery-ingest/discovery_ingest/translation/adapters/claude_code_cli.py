"""The Claude Code transport: the ``claude`` command line, the environment it runs in, and the one subprocess call.

Only :func:`run_subprocess` starts a process. Everything else is pure, and tests inject their own runner in its place.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, Protocol

from discovery_ingest.translation.adapters.cloudflare_prompt import UNITS_SCHEMA

COMMAND: Final = "claude"
TIMEOUT_SECONDS: Final = 240.0
AUTH_VARIABLES: Final = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")
"""Variables that would make the CLI bill an API account instead of the Claude Code login: never passed on."""


@dataclass(frozen=True, slots=True)
class CliRequest:
    """One ``claude`` call: the argument list, the prompt for stdin, the environment and the time it may take."""

    argv: tuple[str, ...]
    stdin: str
    env: Mapping[str, str]
    timeout_seconds: float


@dataclass(frozen=True, slots=True)
class CliResult:
    """What the CLI printed and how it exited."""

    returncode: int
    stdout: str
    stderr: str


class CliTimeout(Exception):
    """The CLI did not finish within its time limit."""


class CliRunner(Protocol):
    """Run one request and return what it printed; raise :class:`CliTimeout` when it runs out of time."""

    def __call__(self, request: CliRequest) -> CliResult:
        """Run ``request``."""
        ...


def subprocess_env(environ: Mapping[str, str]) -> dict[str, str]:
    """Return ``environ`` without the variables that would switch the CLI to API billing."""
    return {name: value for name, value in environ.items() if name not in AUTH_VARIABLES}


def build_request(prompt: str, model: str, environ: Mapping[str, str]) -> CliRequest:
    """Return the request for one batch: no tools, the answer schema, the model, no saved session, the prompt on stdin."""
    argv = (
        COMMAND,
        "--print",
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(UNITS_SCHEMA),
        "--model",
        model,
        "--tools",
        "",
        "--no-session-persistence",
    )
    return CliRequest(argv, prompt, subprocess_env(environ), TIMEOUT_SECONDS)


def run_subprocess(request: CliRequest) -> CliResult:
    """Start the CLI with ``request`` and wait for it; a run that outlives its time limit raises :class:`CliTimeout`."""
    try:
        done = subprocess.run(
            request.argv,
            input=request.stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=dict(request.env),
            timeout=request.timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as err:
        raise CliTimeout(f"no answer within {request.timeout_seconds:g} seconds") from err
    return CliResult(done.returncode, done.stdout, done.stderr)
