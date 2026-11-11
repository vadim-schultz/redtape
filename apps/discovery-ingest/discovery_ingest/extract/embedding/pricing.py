"""Neurons per embedding call: what the provider reported, else the input tokens priced from ``extract/llm/prices.py``."""

from __future__ import annotations

from discovery_ingest.extract.embedding.client import EmbeddingResult
from discovery_ingest.extract.llm.prices import EMBEDDING_NEURONS_PER_MILLION_INPUT_TOKENS, embedding_cost


def reported_neurons(result: EmbeddingResult) -> float | None:
    """Return what ``result`` cost (the reported figure, else its tokens priced), or ``None`` with nothing to go on."""
    if result.neurons is not None:
        return result.neurons
    if result.input_tokens is None or result.model not in EMBEDDING_NEURONS_PER_MILLION_INPUT_TOKENS:
        return None
    return embedding_cost(result.model, result.input_tokens)


def neurons_of(result: EmbeddingResult) -> float:
    """Return the neurons ``result`` cost, or 0 when neither the response nor the price table says."""
    return reported_neurons(result) or 0.0
