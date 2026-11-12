"""Read what ``claude --print --output-format json`` answered: the answer as JSON text, and the tokens the call used.

A readable answer is the schema-checked ``structured_output``, or the ``result`` text when the CLI gave no structured
output. An answer that cannot be read comes back with empty text, so that :func:`parse_answer` rejects it and the
translator repeats the call once. A failed call raises the port category :func:`failure_for` names.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from pydantic import BaseModel, JsonValue, ValidationError

from discovery_ingest.translation.adapters.claude_code_cli import CliResult
from discovery_ingest.translation.adapters.claude_code_errors import failure_for


class CliUsage(BaseModel):
    """The token counts of one call, as the CLI reports them; a count that is absent or null is zero."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_creation_input_tokens: int | None = None
    cache_read_input_tokens: int | None = None


class CliEnvelope(BaseModel):
    """The JSON object the CLI prints: whether it failed, its result text, the schema-checked output and the usage."""

    is_error: bool = False
    result: str | None = None
    structured_output: JsonValue | None = None
    usage: CliUsage | None = None


@dataclass(frozen=True, slots=True)
class CliAnswer:
    """The answer as JSON text (empty when it could not be read) and the tokens the call used."""

    answer_json: str
    tokens: int


def read_answer(result: CliResult) -> CliAnswer:
    """Return the answer of a call that ran; a call that failed raises the category its output names."""
    envelope = _envelope(result.stdout)
    if result.returncode != 0 or (envelope is not None and envelope.is_error):
        raise failure_for(result, envelope.result if envelope is not None else None)
    if envelope is None:
        return CliAnswer("", 0)
    return CliAnswer(_answer_json(envelope), _tokens(envelope))


def _envelope(stdout: str) -> CliEnvelope | None:
    try:
        return CliEnvelope.model_validate_json(stdout)
    except ValidationError:
        return None


def _answer_json(envelope: CliEnvelope) -> str:
    if envelope.structured_output is not None:
        return json.dumps(envelope.structured_output)
    return envelope.result or ""


def _tokens(envelope: CliEnvelope) -> int:
    """All the tokens the call used: input, output and both kinds of prompt cache."""
    usage = envelope.usage or CliUsage()
    counts = (usage.input_tokens, usage.output_tokens, usage.cache_creation_input_tokens, usage.cache_read_input_tokens)
    return sum(count or 0 for count in counts)
