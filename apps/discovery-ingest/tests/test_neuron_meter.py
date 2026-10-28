"""The neuron price table, the estimate and the cost formula (chapter E4, loop B)."""

from __future__ import annotations

import math

import pytest
from discovery_ingest.extract.llm.prices import (
    PROMPT_OVERHEAD_TOKENS,
    UnknownModelError,
    cost,
    estimate,
    known_models,
)

LLAMA_8B = "@cf/meta/llama-3.1-8b-instruct"
LLAMA_70B = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"


def test_estimate_uses_the_model_prices_and_grows_with_input_and_max_tokens() -> None:
    """estimate · ceil(chars/3 and the prompt overhead at the input price plus max_tokens at the output price)."""
    tokens_in = 3000 / 3 + PROMPT_OVERHEAD_TOKENS
    expected_8b = tokens_in * 25_608 / 1e6 + 1000 * 75_147 / 1e6
    expected_70b = tokens_in * 26_668 / 1e6 + 1000 * 204_805 / 1e6

    assert estimate(LLAMA_8B, 3000, 1000) == math.ceil(expected_8b)
    assert estimate(LLAMA_70B, 3000, 1000) == math.ceil(expected_70b)
    assert estimate(LLAMA_8B, 6000, 1000) > estimate(LLAMA_8B, 3000, 1000)
    assert estimate(LLAMA_8B, 3000, 2000) > estimate(LLAMA_8B, 3000, 1000)
    assert estimate(LLAMA_70B, 3000, 1000) > estimate(LLAMA_8B, 3000, 1000)


def test_cost_prices_the_reported_tokens() -> None:
    """cost · tokens in and out times the model's neurons per million, unrounded."""
    assert cost(LLAMA_8B, 1_000_000, 0) == 25_608
    assert cost(LLAMA_8B, 0, 1_000_000) == 75_147
    assert cost(LLAMA_70B, 2000, 500) == pytest.approx(2000 * 26_668 / 1e6 + 500 * 204_805 / 1e6)


def test_an_unknown_model_is_refused_rather_than_guessed() -> None:
    """estimate and cost · a model without a price row raise UnknownModelError naming it."""
    with pytest.raises(UnknownModelError, match="mystery-model"):
        estimate("@cf/acme/mystery-model", 3000, 1000)
    with pytest.raises(UnknownModelError, match="mystery-model"):
        cost("@cf/acme/mystery-model", 10, 10)


def test_the_table_lists_the_six_documented_models() -> None:
    """prices · the initial rows from Cloudflare's pricing page are present."""
    models = known_models()

    assert len(models) == 6
    assert LLAMA_8B in models and LLAMA_70B in models
    assert "@cf/openai/gpt-oss-20b" in models
