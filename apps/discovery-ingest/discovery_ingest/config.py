"""Environment-backed settings for ingest workers."""

from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from discovery_ingest.llm_settings import LlmSettings

DEFAULT_BOT_CONTACT_URL = "https://github.com/vadim-schultz/redtape"
BOT_PRODUCT_TOKEN = "RedtapeBot"


def build_user_agent(contact_url: str) -> str:
    """Return the identifying ``User-Agent`` for the crawl bot."""
    return f"{BOT_PRODUCT_TOKEN}/1.0 (+{contact_url})"


class BrowserSettings(BaseSettings):
    """Cloudflare Browser Run credentials and pacing; nothing is required unless a browser kind is drained.

    Read from the process environment only (no dotenv file), so ``browser probe`` never touches other secrets.
    """

    model_config = SettingsConfigDict(extra="ignore")

    cloudflare_account_id: str | None = Field(default=None, validation_alias="CLOUDFLARE_ACCOUNT_ID")
    cloudflare_browser_api_token: SecretStr | None = Field(
        default=None, validation_alias="CLOUDFLARE_BROWSER_API_TOKEN"
    )
    browser_min_interval_seconds: float = Field(default=11.0, gt=0, validation_alias="BROWSER_MIN_INTERVAL_SECONDS")
    browser_request_timeout_seconds: float = Field(
        default=60.0, gt=0, validation_alias="BROWSER_REQUEST_TIMEOUT_SECONDS"
    )

    def credentials(self) -> tuple[str, str]:
        """Return the account id and the API token, or raise :class:`ValueError` naming what is missing."""
        token = self.cloudflare_browser_api_token
        if not self.cloudflare_account_id or token is None:
            raise ValueError(f"missing {', '.join(self.missing_credentials())}")
        return self.cloudflare_account_id, token.get_secret_value()

    def missing_credentials(self) -> list[str]:
        """Return the names (never the values) of the Cloudflare variables that are not set."""
        names = {
            "CLOUDFLARE_ACCOUNT_ID": self.cloudflare_account_id,
            "CLOUDFLARE_BROWSER_API_TOKEN": self.cloudflare_browser_api_token,
        }
        return [name for name, value in names.items() if not value]


class IngestSettings(BrowserSettings, LlmSettings):
    """Discovery machine API, optional GovData CKAN overrides and the optional browser and Workers AI settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    discovery_api_url: str = Field(validation_alias="DISCOVERY_API_URL")
    discovery_api_key: SecretStr = Field(validation_alias="DISCOVERY_API_KEY")
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
    bot_contact_url: str = Field(
        default=DEFAULT_BOT_CONTACT_URL,
        validation_alias="BOT_CONTACT_URL",
    )

    @property
    def user_agent(self) -> str:
        """Identifying ``User-Agent`` carrying the configured contact URL."""
        return build_user_agent(self.bot_contact_url)


def load_ingest_settings() -> IngestSettings:
    """Load settings from environment variables."""
    return IngestSettings()


def load_browser_settings() -> BrowserSettings:
    """Load only the Cloudflare browser settings from the environment."""
    return BrowserSettings()
