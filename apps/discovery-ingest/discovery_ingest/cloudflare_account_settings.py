"""The Cloudflare account id, declared once for every settings class that talks to Cloudflare."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CloudflareAccountSettings(BaseSettings):
    """The Cloudflare account id shared by the Browser Run and Workers AI settings; never a secret."""

    model_config = SettingsConfigDict(extra="ignore")

    cloudflare_account_id: str | None = Field(default=None, validation_alias="CLOUDFLARE_ACCOUNT_ID")
