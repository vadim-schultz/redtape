"""Price rows for the Mistral Small 3.1 and Llama 4 Scout candidates (chapter E17, loop A)."""

from __future__ import annotations

import pytest
from discovery_ingest.extract.llm.client import LlmResult
from discovery_ingest.extract.llm.prices import (
    UnknownModelError,
    actual_neurons,
    cost,
    estimate,
    known_models,
    reserved_output_tokens,
)

MISTRAL = "@cf/mistralai/mistral-small-3.1-24b-instruct"
SCOUT = "@cf/meta/llama-4-scout-17b-16e-instruct"
LLAMA_70B = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"

# Probe 2026-10-28, page aa-ferienbeschaeftigung: (model, prompt tokens, completion tokens, neurons reported by run usage).
RECORDED_USAGE = [(MISTRAL, 2351, 602, 105.33425903320312), (SCOUT, 2139, 582, 97.47545623779297)]


@pytest.mark.parametrize("model", [MISTRAL, SCOUT])
def test_both_candidate_models_have_a_price_row_and_are_accepted_by_the_meter(model: str) -> None:
    """prices · the row exists, so estimate and cost price the model instead of refusing it."""
    assert model in known_models()
    assert estimate(model, 3000, 1000) > 0
    assert cost(model, 1000, 1000) > 0


@pytest.mark.parametrize(("model", "prompt_tokens", "completion_tokens", "reported"), RECORDED_USAGE)
def test_the_priced_tokens_of_a_recorded_usage_block_are_within_ten_percent_of_the_reported_neurons(
    model: str, prompt_tokens: int, completion_tokens: int, reported: float
) -> None:
    """cost · the table reproduces what the API reported for the recorded call, and a reported figure still wins."""
    assert cost(model, prompt_tokens, completion_tokens) == pytest.approx(reported, rel=0.10)
    result = LlmResult("{}", prompt_tokens, completion_tokens, model, reported)
    assert actual_neurons(result) == reported
    assert actual_neurons(LlmResult("{}", prompt_tokens, completion_tokens, model, None)) == pytest.approx(
        reported, rel=0.10
    )


def test_an_unknown_model_id_is_still_refused_next_to_the_new_rows() -> None:
    """estimate · a near miss of a candidate id has no row and raises UnknownModelError naming it."""
    with pytest.raises(UnknownModelError, match="mistral-small-3.2"):
        estimate("@cf/mistralai/mistral-small-3.2-24b-instruct", 3000, 1000)
    with pytest.raises(UnknownModelError, match="llama-4-maverick"):
        cost("@cf/meta/llama-4-maverick-17b-128e-instruct", 10, 10)


@pytest.mark.parametrize("model", [MISTRAL, SCOUT])
def test_the_reservation_of_a_30000_character_page_stays_under_the_per_page_maximum(model: str) -> None:
    """reservation · the page-sized reserve is below the full 4,000-token limit and below the 70B's 892."""
    reserved = estimate(model, 30_000, reserved_output_tokens(30_000, 4000))

    assert reserved < estimate(model, 30_000, 4000)
    assert reserved < estimate(LLAMA_70B, 30_000, reserved_output_tokens(30_000, 4000))
