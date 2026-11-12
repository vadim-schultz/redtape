"""Azure AI Translator credentials and endpoint, read from the environment; required only by azure-translator."""

from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_AZURE_ENDPOINT = "https://api.cognitive.microsofttranslator.com"
"""The global host. A custom-domain endpoint in an EU region is the operator's choice (O5), set by variable."""

DEFAULT_AZURE_API_VERSION = "2026-06-06"
"""The API version the request and answer shapes are written for; the v3.0 API is not compatible with them."""


class AzureTranslatorSettings(BaseSettings):
    """The Azure Translator key, resource region, endpoint and API version, read from the process environment only.

    The key is a secret: it is never printed, logged or put in an error message.
    """

    model_config = SettingsConfigDict(extra="ignore")

    azure_translator_key: SecretStr | None = Field(default=None, validation_alias="AZURE_TRANSLATOR_KEY")
    azure_translator_region: str | None = Field(default=None, validation_alias="AZURE_TRANSLATOR_REGION")
    azure_translator_endpoint: str = Field(
        default=DEFAULT_AZURE_ENDPOINT, min_length=1, validation_alias="AZURE_TRANSLATOR_ENDPOINT"
    )
    azure_translator_api_version: str = Field(
        default=DEFAULT_AZURE_API_VERSION, min_length=1, validation_alias="AZURE_TRANSLATOR_API_VERSION"
    )

    def credentials(self) -> tuple[str, str]:
        """Return the key value and the region, or raise :class:`ValueError` naming the variables that are not set."""
        key, region = self.azure_translator_key, self.azure_translator_region
        if key is None or not key.get_secret_value() or not region:
            raise ValueError(f"missing {', '.join(self._missing())}")
        return key.get_secret_value(), region

    def _missing(self) -> list[str]:
        """Return the names (never the values) of the credential variables that are not set."""
        names = {
            "AZURE_TRANSLATOR_KEY": self.azure_translator_key,
            "AZURE_TRANSLATOR_REGION": self.azure_translator_region,
        }
        return [name for name, value in names.items() if not value]


def load_azure_translator_settings() -> AzureTranslatorSettings:
    """Load only the Azure Translator settings from the environment."""
    return AzureTranslatorSettings()
