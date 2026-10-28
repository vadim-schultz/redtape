"""Neuron prices per model and the two formulas that use them; the only place either lives."""

from __future__ import annotations

import math
from dataclasses import dataclass

CHARS_PER_TOKEN = 3
PROMPT_OVERHEAD_TOKENS = 1500
"""Input tokens the system prompt and the vocabulary add to every call, on top of the page text."""


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
}
"""Initial rows from Cloudflare's pricing page. The gemma and qwen ids are best guesses until the probe accepts them."""


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


def cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Return the neurons that ``input_tokens`` and ``output_tokens`` cost on ``model``."""
    price = _price(model)
    return (input_tokens * price.per_million_input + output_tokens * price.per_million_output) / 1e6
