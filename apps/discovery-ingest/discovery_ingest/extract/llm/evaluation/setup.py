"""What one eval run measures: the model, the prompt version, the vocabulary and the call limits."""

from __future__ import annotations

from dataclasses import dataclass

from discovery_ingest.extract.llm.taxonomy import Taxonomy


@dataclass(frozen=True, slots=True)
class EvalSetup:
    """The model and prompt under test, the tag vocabulary, the per-call limits and the run's neuron budget."""

    model: str
    prompt_version: str
    taxonomy: Taxonomy
    max_tokens: int
    max_chars: int
    neuron_budget: float
