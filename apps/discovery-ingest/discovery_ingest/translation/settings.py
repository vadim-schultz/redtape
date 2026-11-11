"""Worker-side translation settings: which engine and, optionally, which model; validated at load."""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from discovery_ingest.translation.registry import UnknownEngineError, require_registered

DEFAULT_ENGINE = "llm"
DEFAULT_QUERY_EMBED_RESERVE = 1000.0
"""Neurons of the day's ledger the translate drain leaves for request-time query embedding (about 0.1 a query)."""


class TranslationSettings(BaseSettings):
    """``TRANSLATION_ENGINE``, ``TRANSLATION_MODEL`` and ``QUERY_EMBED_RESERVE``, read from the process environment only."""

    model_config = SettingsConfigDict(extra="ignore")

    translation_engine: str = Field(default=DEFAULT_ENGINE, validation_alias="TRANSLATION_ENGINE")
    translation_model: str | None = Field(default=None, min_length=1, validation_alias="TRANSLATION_MODEL")
    query_embed_reserve: float = Field(
        default=DEFAULT_QUERY_EMBED_RESERVE, ge=0, validation_alias="QUERY_EMBED_RESERVE"
    )

    @field_validator("translation_engine")
    @classmethod
    def _registered(cls, name: str) -> str:
        try:
            return require_registered(name)
        except UnknownEngineError as err:
            raise ValueError(str(err)) from err


def load_translation_settings() -> TranslationSettings:
    """Load the translation settings from the environment."""
    return TranslationSettings()


class ProbeSourceSettings(BaseSettings):
    """Where ``translate probe`` reads the public candidate list: ``DISCOVERY_API_URL`` only, no key."""

    model_config = SettingsConfigDict(extra="ignore")

    discovery_api_url: str | None = Field(default=None, validation_alias="DISCOVERY_API_URL")

    def missing(self) -> list[str]:
        """Return the names (never values) of the variables that are not set."""
        return [] if self.discovery_api_url else ["DISCOVERY_API_URL"]
