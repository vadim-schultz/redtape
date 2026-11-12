"""Azure settings · the endpoint and API version defaults, the secret key, and the registration that keeps llm the default."""

from __future__ import annotations

import pytest
from discovery_ingest.translation.azure_settings import AzureTranslatorSettings, load_azure_translator_settings
from discovery_ingest.translation.registry import registered_engines
from discovery_ingest.translation.settings import TranslationSettings

from azure_transport import KEY, REGION

AZURE_VARIABLES = (
    "AZURE_TRANSLATOR_KEY",
    "AZURE_TRANSLATOR_REGION",
    "AZURE_TRANSLATOR_ENDPOINT",
    "AZURE_TRANSLATOR_API_VERSION",
    "TRANSLATION_ENGINE",
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


def test_azure_is_registered_but_the_default_engine_stays_llm() -> None:
    """Settings · azure-translator can be selected by name; TRANSLATION_ENGINE still defaults to llm."""
    assert "azure-translator" in registered_engines()
    assert TranslationSettings.model_validate({}).translation_engine == "llm"
    assert TranslationSettings.model_validate({"TRANSLATION_ENGINE": "azure-translator"}).translation_engine == (
        "azure-translator"
    )
