"""What an llm_extract drain needs besides the machine client and the neuron meter: the model, its limits, the vocabulary."""

from __future__ import annotations

from dataclasses import dataclass

from discovery_ingest.extract.llm.client import LlmClient
from discovery_ingest.extract.llm.taxonomy import Taxonomy

DEFAULT_MAX_TOKENS = 1500
DEFAULT_MAX_CHARS = 12000


@dataclass(frozen=True, slots=True)
class LlmResources:
    """The model client and id, the tag vocabulary, the output token cap and the cleaned-text cap of every call."""

    client: LlmClient
    taxonomy: Taxonomy
    model: str
    max_tokens: int = DEFAULT_MAX_TOKENS
    max_chars: int = DEFAULT_MAX_CHARS
