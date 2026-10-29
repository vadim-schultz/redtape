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
    reserved_output_tokens,
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


def test_the_table_lists_the_documented_models() -> None:
    """prices · the initial rows and the two candidate rows are present."""
    models = known_models()

    assert len(models) == 8
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


RECORDED_ANSWERS = [  # (prompt tokens, completion tokens) of the 19 recorded gold-page answers, 2026-10-28
    (1561, 29), (1586, 31), (1603, 36), (1699, 219), (1734, 29), (1772, 455), (1919, 223), (2277, 822), (2397, 31),
    (2439, 558), (2607, 293), (2785, 29), (2977, 77), (3225, 837), (3482, 29), (4635, 701), (4898, 29), (5081, 29),
    (5089, 484),
]  # fmt: skip


def test_the_largest_reservation_for_a_30000_character_page_stays_below_the_daily_cap() -> None:
    """estimate · 30,000 characters in and the 4,000-token limit out is about 1,100 neurons, far below 9,500."""
    assert 1000 < estimate(LLAMA_70B, 30_000, 4000) < 1200


def test_the_reservation_is_an_upper_bound_of_the_recorded_probe_cost() -> None:
    """reservation · the page-sized output reserve for the probe page is above the 160.1 neurons the API reported."""
    reserved = estimate(LLAMA_70B, RECORDED_PAGE_CHARS, reserved_output_tokens(RECORDED_PAGE_CHARS, 4000))

    assert RECORDED_NEURONS < reserved < estimate(LLAMA_70B, RECORDED_PAGE_CHARS, 4000)


@pytest.mark.parametrize(("prompt_tokens", "completion_tokens"), RECORDED_ANSWERS)
def test_the_reservation_bounds_every_recorded_answer(prompt_tokens: int, completion_tokens: int) -> None:
    """reservation · for each recorded page the page-sized reserve covers what the call really cost."""
    chars = (prompt_tokens - PROMPT_OVERHEAD_TOKENS) * 3
    reserved = estimate(LLAMA_70B, chars, reserved_output_tokens(chars, 4000))

    assert reserved >= cost(LLAMA_70B, prompt_tokens, completion_tokens)


def test_the_output_reserve_grows_with_the_page_and_never_passes_the_limit() -> None:
    """reservation · a short page reserves a floor, a 30,000-character page about 3,000 tokens, a small limit caps both."""
    assert 400 <= reserved_output_tokens(100, 4000) < reserved_output_tokens(30_000, 4000) < 4000
    assert reserved_output_tokens(30_000, 800) == 800 and reserved_output_tokens(100, 300) == 300
