"""Fakes for the Claude Code engine: a scripted ``claude`` runner that answers in the CLI's JSON envelope.

No test spawns ``claude``: every request goes to a :class:`FakeCli`, which records it and answers with a reply function.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field

from discovery_ingest.translation.adapters.claude_code_cli import CliRequest, CliResult, CliTimeout

MODEL = "claude-sonnet-5-5"
SECRET = "sk-ant-api03-SECRET-0123456789"
USAGE = {"input_tokens": 1000, "output_tokens": 300, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}
MARKER = "User message:\n"
Reply = Callable[[CliRequest], CliResult]


def units_in(request: CliRequest) -> list[dict[str, str]]:
    """Return the units the adapter put into the prompt (the CLI reads the prompt from stdin)."""
    return json.loads(request.stdin.split(MARKER, 1)[1])["units"]


def envelope(structured: dict[str, object] | None = None, *, result: str = "", is_error: bool = False) -> str:
    """The JSON that ``claude --print --output-format json`` prints; ``structured_output`` only when a schema was given."""
    body: dict[str, object] = {"type": "result", "is_error": is_error, "result": result, "usage": USAGE}
    if structured is not None:
        body["structured_output"] = structured
    return json.dumps(body)


def faithful(units: list[dict[str, str]]) -> dict[str, object]:
    """Translate by prefixing, so every number, date, URL and citation of the source survives."""
    return {
        "units": [
            {
                "key": unit["key"],
                "title": f"[en] {unit['title']}",
                "description": f"[en] {unit['description']}" if unit["description"] else "",
            }
            for unit in units
        ]
    }


def answered(request: CliRequest, *, drop: int = 0) -> CliResult:
    """A readable answer for every unit of the request except the last ``drop`` ones."""
    units = units_in(request)
    return CliResult(0, envelope(faithful(units[: len(units) - drop])), "")


@dataclass
class FakeCli:
    """A ``claude`` stand-in: it records each request and answers it with ``reply``."""

    reply: Reply
    requests: list[CliRequest] = field(default_factory=list)

    def __call__(self, request: CliRequest) -> CliResult:
        """Record ``request`` and return the scripted answer."""
        self.requests.append(request)
        return self.reply(request)


def canned(returncode: int, stdout: str, stderr: str) -> Reply:
    """A reply that ignores the request and always prints the same thing."""
    return lambda _request: CliResult(returncode, stdout, stderr)


def timeout_reply(_request: CliRequest) -> CliResult:
    """A call that never finishes in time."""
    raise CliTimeout(f"no answer within 240 seconds ({SECRET})")


QUOTA_REPLY = canned(1, envelope(is_error=True, result=f"Claude AI usage limit reached|1760000000 ({SECRET})"), "")
UNAUTHORISED_REPLY = canned(
    1, envelope(is_error=True, result=f"Not logged in · Please run /login ({SECRET})"), f"token {SECRET}"
)
PERMANENT_REPLY = canned(
    1,
    envelope(
        is_error=True,
        result="There's an issue with the selected model. It may not exist or you may not have access to it.",
    ),
    "",
)
