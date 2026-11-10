"""Neurons per embedding call: what the provider reported, else the input tokens priced from the table below."""

from __future__ import annotations

from discovery_ingest.extract.embedding.client import EmbeddingResult

NEURONS_PER_MILLION_INPUT_TOKENS: dict[str, float] = {"@cf/qwen/qwen3-embedding-0.6b": 1075.0}
"""Cloudflare's price of an embedding model (inputs only); the probe's reported neurons confirm or correct the row."""


def neurons_of(result: EmbeddingResult) -> float:
    """Return the neurons ``result`` cost: the reported figure, else its tokens priced, else 0 (nothing to go on)."""
    if result.neurons is not None:
        return result.neurons
    price = NEURONS_PER_MILLION_INPUT_TOKENS.get(result.model)
    if price is None or result.input_tokens is None:
        return 0.0
    return result.input_tokens * price / 1e6
