"""The LLM port: what the handler needs from a model provider, nothing about HTTP or the envelope."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol, TypedDict

from discovery_ingest.json_types import JsonSchema


class ChatMessage(TypedDict):
    """One chat message: a system or user instruction and its text."""

    role: Literal["system", "user"]
    content: str


@dataclass(frozen=True, slots=True)
class LlmResult:
    """The model's JSON text, the token counts and the neurons the provider reported (``None`` when it reported none)."""

    parsed_json: str
    input_tokens: int | None
    output_tokens: int | None
    model: str
    neurons: float | None = None


class LlmClient(Protocol):
    """Ask a model for JSON that follows a schema; every call may raise an :class:`LlmError`."""

    def extract(self, messages: Sequence[ChatMessage], json_schema: JsonSchema, *, max_tokens: int) -> LlmResult:
        """Return the model's answer to ``messages`` constrained by ``json_schema``, capped at ``max_tokens``."""
        ...
