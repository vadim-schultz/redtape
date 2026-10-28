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


RECORDED_PAGE_CHARS = 3694
RECORDED_PROMPT_TOKENS = 1597
RECORDED_COMPLETION_TOKENS = 574
RECORDED_NEURONS = 160.1


def test_the_estimated_input_tokens_of_the_recorded_probe_page_are_within_15_percent_of_the_reported_ones() -> None:
    """estimate · 3,694 characters plus the overhead against the 1,597 prompt tokens the API reported (probe 2026-10-28)."""
    estimated = RECORDED_PAGE_CHARS / 3 + PROMPT_OVERHEAD_TOKENS

    assert estimated == pytest.approx(RECORDED_PROMPT_TOKENS, rel=0.15)
    assert PROMPT_OVERHEAD_TOKENS < 600


def test_the_estimate_for_the_recorded_probe_page_is_within_15_percent_of_the_160_neurons_the_api_reported() -> None:
    """estimate · with the completion that call produced, the formula lands on the reported neurons; a cap only adds."""
    estimated = estimate(LLAMA_70B, RECORDED_PAGE_CHARS, RECORDED_COMPLETION_TOKENS)

    assert estimated == pytest.approx(RECORDED_NEURONS, rel=0.15)
    assert estimate(LLAMA_70B, RECORDED_PAGE_CHARS, 1500) > estimated
