"""LlmSettings: optional Workers AI credentials and limits, read from the environment (chapter E4)."""

from __future__ import annotations

import pytest
from discovery_ingest.config import load_ingest_settings
from discovery_ingest.llm_settings import load_llm_settings

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
    """settings · limits default to 1500 tokens, 30000 characters and 60 s; the token stays out of the repr."""
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", ACCOUNT_ID)
    monkeypatch.setenv("CLOUDFLARE_AI_API_TOKEN", TOKEN)

    settings = load_llm_settings()

    assert settings.ai_credentials() == (ACCOUNT_ID, TOKEN)
    assert settings.missing_ai_credentials() == []
    assert (settings.llm_model, settings.llm_max_tokens, settings.llm_input_chars) == (None, 1500, 30000)
    assert settings.llm_request_timeout_seconds == 60.0
    assert TOKEN not in repr(settings)


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
