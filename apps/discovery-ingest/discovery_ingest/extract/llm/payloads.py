"""Request bodies for Workers AI, shared by the client and the probe so the probe tests what the worker sends."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import JsonValue

from discovery_ingest.extract.llm.client import ChatMessage
from discovery_ingest.json_types import JsonObject, JsonSchema

Body = JsonObject
SCHEMA_NAME = "page_extraction"


def _messages(messages: Sequence[ChatMessage]) -> list[JsonValue]:
    return [{"role": message["role"], "content": message["content"]} for message in messages]


def run_body(messages: Sequence[ChatMessage], schema: JsonSchema, max_tokens: int) -> Body:
    """Return the native ``/ai/run`` body: JSON mode with the schema as ``json_schema``."""
    return {
        "messages": _messages(messages),
        "response_format": {"type": "json_schema", "json_schema": schema},
        "max_tokens": max_tokens,
    }


def chat_body(model: str, messages: Sequence[ChatMessage], schema: JsonSchema, max_tokens: int) -> Body:
    """Return the OpenAI-compatible ``/ai/v1/chat/completions`` body (probe only; the schema is named and wrapped)."""
    wrapped: JsonObject = {"name": SCHEMA_NAME, "schema": schema}
    return {
        "model": model,
        "messages": _messages(messages),
        "response_format": {"type": "json_schema", "json_schema": wrapped},
        "max_tokens": max_tokens,
    }
