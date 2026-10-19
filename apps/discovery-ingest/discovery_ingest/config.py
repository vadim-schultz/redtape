"""Environment-backed settings for ingest workers."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class IngestSettings(BaseSettings):
    """Discovery machine API and optional GovData CKAN overrides."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    discovery_api_url: str = Field(validation_alias="DISCOVERY_API_URL")
    discovery_api_key: str = Field(validation_alias="DISCOVERY_API_KEY")
    govdata_ckan_base_url: str = Field(
        default="https://ckan.govdata.de/api/3/action",
        validation_alias="GOVDATA_CKAN_BASE_URL",
    )
    govdata_package_id: str = Field(
        default="ozg-leistungen-und-zugehorige-onlinedienste",
        validation_alias="GOVDATA_PACKAGE_ID",
    )
    govdata_open_pvog_ars: str = Field(
        default="000000000000",
        validation_alias="GOVDATA_OPEN_PVOG_ARS",
    )
    pvog_api_base_url: str = Field(
        default="https://pvog.fitko.net/suchdienst/api",
        validation_alias="PVOG_API_BASE_URL",
    )
    fim_portal_base_url: str = Field(
        default="https://fimportal.de",
        validation_alias="FIM_PORTAL_BASE_URL",
    )


def load_ingest_settings() -> IngestSettings:
    """Load settings from environment variables."""
    return IngestSettings()  # type: ignore[call-arg]
