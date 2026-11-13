"""Azure settings · the endpoint and API version defaults, the secret key, and the engine default (azure-translator)."""

from __future__ import annotations

import pytest
from discovery_ingest.translation.adapters.cloudflare_llm import LlmTranslator
from discovery_ingest.translation.azure_settings import AzureTranslatorSettings, load_azure_translator_settings
from discovery_ingest.translation.registry import EngineConfig, build_engine, registered_engines
from discovery_ingest.translation.settings import TranslationSettings, load_translation_settings
from pydantic import ValidationError

from azure_transport import KEY, REGION

AZURE_VARIABLES = (
    "AZURE_TRANSLATOR_KEY",
    "AZURE_TRANSLATOR_REGION",
    "AZURE_TRANSLATOR_ENDPOINT",
    "AZURE_TRANSLATOR_API_VERSION",
    "TRANSLATION_ENGINE",
    "TRANSLATION_GLOSSARY_MODE",
)


@pytest.fixture(autouse=True)
def _no_azure_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in AZURE_VARIABLES:
        monkeypatch.delenv(name, raising=False)


def test_settings_endpoint_defaults_to_the_global_host_and_the_api_version_to_2026_06_06() -> None:
    """Settings · endpoint defaults to the global host and the API version to 2026-06-06."""
    settings = AzureTranslatorSettings()

    assert settings.azure_translator_endpoint == "https://api.cognitive.microsofttranslator.com"
    assert settings.azure_translator_api_version == "2026-06-06"
    assert (settings.azure_translator_key, settings.azure_translator_region) == (None, None)


def test_settings_read_the_key_region_endpoint_and_version_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Settings · the four variables are read from the process environment under their documented names."""
    monkeypatch.setenv("AZURE_TRANSLATOR_KEY", KEY)
    monkeypatch.setenv("AZURE_TRANSLATOR_REGION", REGION)
    monkeypatch.setenv("AZURE_TRANSLATOR_ENDPOINT", "https://eu.example.test")
    monkeypatch.setenv("AZURE_TRANSLATOR_API_VERSION", "2026-07-01")

    settings = load_azure_translator_settings()

    assert settings.azure_translator_key is not None and settings.azure_translator_key.get_secret_value() == KEY
    assert (settings.azure_translator_region, settings.azure_translator_endpoint) == (REGION, "https://eu.example.test")
    assert settings.azure_translator_api_version == "2026-07-01"


def test_the_key_is_a_secret_and_never_shows_in_the_settings_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings · the key is held as a secret; its value is not in repr or str of the settings object."""
    monkeypatch.setenv("AZURE_TRANSLATOR_KEY", KEY)

    settings = load_azure_translator_settings()

    assert KEY not in repr(settings) and KEY not in str(settings)


def test_credentials_name_the_missing_variables_and_never_their_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings · missing credentials raise a ValueError that names the variables that are not set."""
    monkeypatch.setenv("AZURE_TRANSLATOR_REGION", REGION)

    with pytest.raises(ValueError, match="AZURE_TRANSLATOR_KEY") as raised:
        load_azure_translator_settings().credentials()

    assert REGION not in str(raised.value)


def test_credentials_return_the_key_and_region_when_both_are_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings · with both credentials set, credentials() returns the key value and the region."""
    monkeypatch.setenv("AZURE_TRANSLATOR_KEY", KEY)
    monkeypatch.setenv("AZURE_TRANSLATOR_REGION", REGION)

    assert load_azure_translator_settings().credentials() == (KEY, REGION)


def test_azure_is_registered_and_selectable_by_name() -> None:
    """Settings · azure-translator is registered and can be selected by name."""
    assert "azure-translator" in registered_engines()
    assert TranslationSettings.model_validate({"TRANSLATION_ENGINE": "azure-translator"}).translation_engine == (
        "azure-translator"
    )


def test_with_no_translation_engine_set_the_engine_is_azure_translator() -> None:
    """Settings · with no TRANSLATION_ENGINE set, the engine is azure-translator (chapter 16)."""
    assert load_translation_settings().translation_engine == "azure-translator"


def test_translation_engine_llm_still_selects_the_cloudflare_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings · TRANSLATION_ENGINE=llm still selects the Cloudflare adapter, which is the rollback path."""
    monkeypatch.setenv("TRANSLATION_ENGINE", "llm")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acc0123456789abcdef")
    monkeypatch.setenv("CLOUDFLARE_AI_API_TOKEN", "tok-fake-1234")

    engine = build_engine(
        load_translation_settings().translation_engine, EngineConfig(model="@cf/qwen/qwen3-30b-a3b-fp8")
    )

    assert isinstance(engine, LlmTranslator) and engine.name == "llm"


def test_a_misspelt_engine_name_fails_at_load(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings · a misspelt engine name fails at load, and the message lists the registered engines."""
    monkeypatch.setenv("TRANSLATION_ENGINE", "azure-translater")

    with pytest.raises(ValidationError, match="registered: .*azure-translator"):
        load_translation_settings()


def test_the_glossary_mode_accepts_strict_and_advisory_and_defaults_to_strict() -> None:
    """Settings · TRANSLATION_GLOSSARY_MODE accepts strict and advisory and defaults to strict."""
    assert TranslationSettings.model_validate({}).translation_glossary_mode == "strict"
    assert (
        TranslationSettings.model_validate({"TRANSLATION_GLOSSARY_MODE": "strict"}).translation_glossary_mode
        == "strict"
    )
    assert (
        TranslationSettings.model_validate({"TRANSLATION_GLOSSARY_MODE": "advisory"}).translation_glossary_mode
        == "advisory"
    )


def test_an_unknown_glossary_mode_fails_at_load(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings · an unknown glossary mode fails at load, naming the variable."""
    monkeypatch.setenv("TRANSLATION_GLOSSARY_MODE", "lenient")

    with pytest.raises(ValidationError, match="TRANSLATION_GLOSSARY_MODE"):
        load_translation_settings()
