"""LlmSettings: optional Workers AI credentials and limits, read from the environment (chapter E4)."""

from __future__ import annotations

import json

import pytest
from discovery_ingest.config import load_ingest_settings
from discovery_ingest.extract.llm.schema import MAX_DEPENDENCIES, MAX_DOCUMENTS, PageExtraction
from discovery_ingest.extract.llm.prices import known_models
from discovery_ingest.llm_settings import DEFAULT_LLM_MODEL, load_llm_settings
from discovery_ingest.worker.llm_runtime import LlmResources

ACCOUNT_ID = "acc0123456789abcdef0123456789abc"
TOKEN = "ai-tok-SECRET-0123456789"
NAMES = (
    "CLOUDFLARE_ACCOUNT_ID",
    "CLOUDFLARE_AI_API_TOKEN",
    "LLM_MODEL",
    "LLM_MAX_TOKENS",
    "LLM_INPUT_CHARS",
    "LLM_REQUEST_TIMEOUT_SECONDS",
)


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DISCOVERY_API_URL", "https://redtape.test")
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")


def test_settings_default_the_limits_and_read_the_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """settings · limits default to 4000 tokens, 30000 characters and 60 s; the token stays out of the repr."""
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", ACCOUNT_ID)
    monkeypatch.setenv("CLOUDFLARE_AI_API_TOKEN", TOKEN)

    settings = load_llm_settings()

    assert settings.ai_credentials() == (ACCOUNT_ID, TOKEN)
    assert settings.missing_ai_credentials() == []
    assert (settings.llm_model, settings.llm_max_tokens, settings.llm_input_chars) == (DEFAULT_LLM_MODEL, 4000, 30000)
    assert settings.llm_request_timeout_seconds == 60.0
    assert TOKEN not in repr(settings)


def test_the_default_model_is_the_provisional_x16_choice_and_has_a_price() -> None:
    """settings · LLM_MODEL defaults to the Qwen3-30B-A3B-FP8 id, which has a neuron price row."""
    settings = load_llm_settings()

    assert DEFAULT_LLM_MODEL == "@cf/qwen/qwen3-30b-a3b-fp8"
    assert settings.llm_model == DEFAULT_LLM_MODEL and DEFAULT_LLM_MODEL in known_models()


def test_an_explicit_model_wins_and_an_explicit_empty_one_means_no_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """settings · LLM_MODEL overrides the default; LLM_MODEL= (empty) stays empty so the refusal paths still fire."""
    monkeypatch.setenv("LLM_MODEL", "@cf/meta/llama-3.3-70b-instruct-fp8-fast")
    assert load_llm_settings().llm_model == "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
    monkeypatch.setenv("LLM_MODEL", "")

    assert not load_llm_settings().llm_model


def test_settings_name_missing_variables_without_values_and_refuse_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """settings · missing credentials are listed by name only and ai_credentials() raises."""
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", ACCOUNT_ID)

    settings = load_llm_settings()

    assert settings.missing_ai_credentials() == ["CLOUDFLARE_AI_API_TOKEN"]
    with pytest.raises(ValueError, match="CLOUDFLARE_AI_API_TOKEN") as raised:
        settings.ai_credentials()
    assert ACCOUNT_ID not in str(raised.value)


def test_ingest_settings_carry_the_llm_settings_and_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """settings · IngestSettings reads the same fields and overrides from the environment."""
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", ACCOUNT_ID)
    monkeypatch.setenv("CLOUDFLARE_AI_API_TOKEN", TOKEN)
    monkeypatch.setenv("LLM_MODEL", "@cf/meta/llama-3.1-8b-instruct")
    monkeypatch.setenv("LLM_MAX_TOKENS", "800")

    settings = load_ingest_settings()

    assert settings.llm_model == "@cf/meta/llama-3.1-8b-instruct" and settings.llm_max_tokens == 800
    assert settings.ai_credentials()[0] == ACCOUNT_ID
    assert settings.missing_ai_credentials() == []


def test_llm_limits_must_be_positive(monkeypatch: pytest.MonkeyPatch) -> None:
    """settings · a zero token limit is rejected instead of sent to the model."""
    monkeypatch.setenv("LLM_MAX_TOKENS", "0")

    with pytest.raises(ValueError, match="LLM_MAX_TOKENS"):
        load_llm_settings()


JSON_CHARS_PER_TOKEN = 3.1
"""The fewest JSON characters per token among the ten recorded answers (3.1 to 3.6, 2026-10-28)."""


def _answer(documents: int, dependencies: int, quote_length: int) -> str:
    quote = "Bitte legen Sie " + "x" * (quote_length - 16)
    document = {"name": "Meldebescheinigung", "role": "required", "quote": quote, "url": None, "condition": None}
    dependency = {"parent": "Antrag", "requires": "Meldebescheinigung", "quote": quote, "condition": None}
    answer = {"page_kind": "service", "domain_codes": ["housing"], "situation_codes": []}
    answer |= {"documents": [document] * documents, "dependencies": [dependency] * dependencies}
    return json.dumps(PageExtraction.model_validate(answer).model_dump(mode="json"), ensure_ascii=False)


def test_the_default_output_limit_is_4000_tokens_and_a_worst_case_realistic_answer_fits() -> None:
    """settings · 40 documents and 8 dependencies with 80-character quotes need about 3,900 tokens at the recorded density."""
    limit = load_llm_settings().llm_max_tokens
    realistic = _answer(MAX_DOCUMENTS, 8, quote_length=80)

    assert limit == 4000 == LlmResources.__dataclass_fields__["max_tokens"].default
    assert len(realistic) / JSON_CHARS_PER_TOKEN <= limit


def test_an_answer_with_every_list_full_and_the_longest_quotes_does_not_fit_and_is_left_to_the_repair_path() -> None:
    """settings · the schema maximum (40 + 40 items, 300-character quotes) exceeds the limit, so it ends as invalid output."""
    extreme = _answer(MAX_DOCUMENTS, MAX_DEPENDENCIES, quote_length=300)

    assert len(extreme) / JSON_CHARS_PER_TOKEN > load_llm_settings().llm_max_tokens
