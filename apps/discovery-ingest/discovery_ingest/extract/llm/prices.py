"""Neuron prices per model and the two formulas that use them; the only place either lives."""

from __future__ import annotations

import math
from dataclasses import dataclass

from discovery_ingest.extract.llm.client import LlmResult

CHARS_PER_TOKEN = 3
PROMPT_OVERHEAD_TOKENS = 400
"""Input tokens the prompt and vocabulary add to a page: measured 366 (1,597 prompt tokens for 3,694 characters)."""
OUTPUT_FLOOR_TOKENS = 500
OUTPUT_TOKENS_PER_PAGE_TOKEN = 0.25
"""Output tokens reserved per page token on top of the floor; the 19 recorded answers used 0.0 to 0.43 of their page."""


@dataclass(frozen=True, slots=True)
class NeuronPrice:
    """Neurons per million input tokens and per million output tokens."""

    per_million_input: float
    per_million_output: float


NEURON_PRICES: dict[str, NeuronPrice] = {
    "@cf/meta/llama-3.3-70b-instruct-fp8-fast": NeuronPrice(26_668, 204_805),
    "@cf/meta/llama-3.1-8b-instruct": NeuronPrice(25_608, 75_147),
    "@cf/meta/llama-3.1-8b-instruct-fp8-fast": NeuronPrice(4_119, 34_868),
    "@cf/openai/gpt-oss-20b": NeuronPrice(18_182, 27_273),
    "@cf/google/gemma-4-26b-a4b-it": NeuronPrice(9_091, 27_273),
    "@cf/qwen/qwen3-30b-a3b-fp8": NeuronPrice(4_625, 30_475),
    "@cf/mistralai/mistral-small-3.1-24b-instruct": NeuronPrice(31_876, 50_488),
    "@cf/meta/llama-4-scout-17b-16e-instruct": NeuronPrice(24_545, 77_273),
}
"""Rows from Cloudflare's pricing page (developers.cloudflare.com/workers-ai/platform/pricing/).

The Mistral and Scout rows were fetched on 2026-10-29 and reproduce the neurons the probe of 2026-10-28 reported
(105.33 for 2,351 + 602 tokens, 97.48 for 2,139 + 582). The gemma id is a best guess: that probe timed out on it.
"""


EMBEDDING_NEURONS_PER_MILLION_INPUT_TOKENS: dict[str, float] = {"@cf/qwen/qwen3-embedding-0.6b": 1075.0}
"""Cloudflare's price of an embedding model: inputs only, output tokens are not billed.

The embed probe of 2026-11-10 measured 1.07 neurons per thousand input tokens (8.52 neurons for 7,931 tokens), which
confirms the 1,075 of the pricing page.
"""


class UnknownModelError(ValueError):
    """The model has no price row; a model is refused rather than guessed."""


def known_models() -> tuple[str, ...]:
    """Return the model ids that have a price row."""
    return tuple(NEURON_PRICES)


def _price(model: str) -> NeuronPrice:
    try:
        return NEURON_PRICES[model]
    except KeyError:
        raise UnknownModelError(f"no neuron price for model {model}") from None


def estimate(model: str, input_chars: int, max_tokens: int) -> int:
    """Return the neurons to reserve for one call: the page and prompt in, ``max_tokens`` out, rounded up."""
    price = _price(model)
    tokens_in = input_chars / CHARS_PER_TOKEN + PROMPT_OVERHEAD_TOKENS
    return math.ceil((tokens_in * price.per_million_input + max_tokens * price.per_million_output) / 1e6)


def reserved_output_tokens(input_chars: int, max_tokens: int) -> int:
    """Return the answer tokens to reserve for a page of ``input_chars``: a floor plus a share of the page, never above ``max_tokens``.

    The answer lists what the page names, so it grows with the page; reserving the full limit for every page would
    leave a 30,000-character budget for about four pages. Settlement corrects the reservation to the reported cost.
    """
    page_tokens = input_chars / CHARS_PER_TOKEN
    return min(max_tokens, OUTPUT_FLOOR_TOKENS + math.ceil(page_tokens * OUTPUT_TOKENS_PER_PAGE_TOKEN))


def cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Return the neurons that ``input_tokens`` and ``output_tokens`` cost on ``model``."""
    price = _price(model)
    return (input_tokens * price.per_million_input + output_tokens * price.per_million_output) / 1e6


def _embedding_price(model: str) -> float:
    try:
        return EMBEDDING_NEURONS_PER_MILLION_INPUT_TOKENS[model]
    except KeyError:
        raise UnknownModelError(f"no neuron price for embedding model {model}") from None


def estimate_embedding(model: str, input_chars: int) -> int:
    """Return the neurons to reserve for embedding ``input_chars`` of text: characters over three, priced, rounded up."""
    return max(1, math.ceil(embedding_cost(model, math.ceil(input_chars / CHARS_PER_TOKEN))))


def embedding_cost(model: str, input_tokens: int) -> float:
    """Return the neurons that ``input_tokens`` cost on the embedding ``model``."""
    return input_tokens * _embedding_price(model) / 1e6


def actual_neurons(result: LlmResult) -> float | None:
    """Return what ``result`` cost: the neurons the provider reported, else its tokens priced, else ``None``."""
    if result.neurons is not None:
        return result.neurons
    if result.input_tokens is None or result.output_tokens is None:
        return None
    return cost(result.model, result.input_tokens, result.output_tokens)
