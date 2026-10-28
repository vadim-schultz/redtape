"""Describe a response by shape and size only: bodies are never echoed, only named fields (probe items 1 and 2)."""

from __future__ import annotations

from collections.abc import Iterator

from pydantic import JsonValue

from discovery_ingest.extract.llm.classify import describe
from discovery_ingest.extract.llm.probe_calls import RawCall


def kind(value: JsonValue) -> str:
    """Name the JSON type of ``value``; a string also shows its length."""
    if isinstance(value, str):
        return f"string[{len(value)} chars]"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return f"array[{len(value)}]"
    return "missing" if value is None else type(value).__name__


def failure_text(call: RawCall) -> str:
    """Say why ``call`` has no usable answer: the transport error or ``HTTP <status> code <code>: <message>``."""
    if call.response is None:
        return call.error or "no response"
    return describe(call.response, lambda text: text)


def fields(value: JsonValue) -> dict[str, JsonValue]:
    """Return ``value`` when it is a JSON object, else an empty one."""
    return value if isinstance(value, dict) else {}


def flatten(prefix: str, value: JsonValue) -> Iterator[str]:
    """Yield ``path=value`` for every numeric leaf of ``value`` and ``path=kind`` for other leaves."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield from flatten(f"{prefix}.{key}" if prefix else key, item)
    elif isinstance(value, int | float) and not isinstance(value, bool):
        yield f"{prefix}={value}"
    else:
        yield f"{prefix}={kind(value)}"


def reasoning_notes(payload: JsonValue, path: str = "") -> Iterator[str]:
    """Yield every field whose name mentions reasoning, with its value or its kind (probe item 2)."""
    for key, item in fields(payload).items():
        here = f"{path}.{key}" if path else key
        if "reason" in key.lower():
            yield from flatten(here, item)
        else:
            yield from reasoning_notes(item, here)
