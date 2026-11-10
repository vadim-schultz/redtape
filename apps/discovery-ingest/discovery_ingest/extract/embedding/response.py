"""Read the vectors and usage out of a successful embedding ``/ai/run`` response (``result.data``, ``result.usage``)."""

from __future__ import annotations

from dataclasses import dataclass

import httpx
from pydantic import BaseModel, JsonValue, ValidationError

from discovery_ingest.extract.llm.classify import json_payload
from discovery_ingest.extract.llm.envelope import reported_neurons, token_count
from discovery_ingest.extract.llm.errors import LlmInvalidOutput

Vector = tuple[float, ...]


class EmbeddingBody(BaseModel):
    """The ``result`` object of an embedding answer: one vector per input text and an optional usage block."""

    data: list[list[float]]
    usage: JsonValue = None


@dataclass(frozen=True, slots=True)
class ParsedEmbeddings:
    """The vectors of one answer, their common dimension, and the tokens and neurons the provider reported."""

    vectors: tuple[Vector, ...]
    dimension: int
    input_tokens: int | None
    neurons: float | None


def _body(response: httpx.Response) -> EmbeddingBody:
    payload = json_payload(response)
    result = payload.get("result") if payload and payload.get("success") is True else None
    try:
        return EmbeddingBody.model_validate(result)
    except ValidationError as err:
        raise LlmInvalidOutput("Cloudflare answered 200 without embedding vectors") from err


def _dimension(vectors: tuple[Vector, ...]) -> int:
    widths = {len(vector) for vector in vectors}
    if len(widths) != 1 or 0 in widths:
        raise LlmInvalidOutput(f"the vectors do not share one non-zero dimension: {sorted(widths)}")
    return widths.pop()


def _usage_fields(body: EmbeddingBody) -> dict[str, JsonValue]:
    return body.usage if isinstance(body.usage, dict) else {}


def read_embeddings(response: httpx.Response, expected: int) -> ParsedEmbeddings:
    """Return the parsed 2xx ``response`` for ``expected`` texts, or raise :class:`LlmInvalidOutput`."""
    body = _body(response)
    if len(body.data) != expected:
        raise LlmInvalidOutput(f"the response has {len(body.data)} vectors for {expected} texts")
    vectors = tuple(tuple(vector) for vector in body.data)
    usage = _usage_fields(body)
    tokens = token_count(usage.get("prompt_tokens", usage.get("total_tokens")))
    return ParsedEmbeddings(vectors, _dimension(vectors), tokens, reported_neurons(usage.get("neurons")))
