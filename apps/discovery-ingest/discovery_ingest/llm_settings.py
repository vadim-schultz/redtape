"""Workers AI credentials and limits; nothing is required unless ``llm_extract`` is drained or ``llm probe`` runs."""

from __future__ import annotations

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from discovery_ingest.extract.clean import DEFAULT_MAX_CHARS

DEFAULT_MAX_TOKENS = 4000
"""The output limit of one model call; enough for a long answer, and the one number the handler imports too."""


class LlmSettings(BaseSettings):
    """Cloudflare Workers AI credentials and call limits, read from the process environment only.

    The token is a custom token with only the Workers AI permission; it is never a Render variable.
    """

    model_config = SettingsConfigDict(extra="ignore")

    cloudflare_account_id: str | None = Field(default=None, validation_alias="CLOUDFLARE_ACCOUNT_ID")
    cloudflare_ai_api_token: SecretStr | None = Field(default=None, validation_alias="CLOUDFLARE_AI_API_TOKEN")
    llm_model: str | None = Field(default=None, validation_alias="LLM_MODEL")
    llm_max_tokens: int = Field(default=DEFAULT_MAX_TOKENS, gt=0, validation_alias="LLM_MAX_TOKENS")
    llm_input_chars: int = Field(default=DEFAULT_MAX_CHARS, gt=0, validation_alias="LLM_INPUT_CHARS")
    llm_request_timeout_seconds: float = Field(default=60.0, gt=0, validation_alias="LLM_REQUEST_TIMEOUT_SECONDS")

    def ai_credentials(self) -> tuple[str, str]:
        """Return the account id and the AI token, or raise :class:`ValueError` naming what is missing."""
        token = self.cloudflare_ai_api_token
        if not self.cloudflare_account_id or token is None:
            raise ValueError(f"missing {', '.join(self.missing_ai_credentials())}")
        return self.cloudflare_account_id, token.get_secret_value()

    def missing_ai_credentials(self) -> list[str]:
        """Return the names (never the values) of the Workers AI variables that are not set."""
        names = {
            "CLOUDFLARE_ACCOUNT_ID": self.cloudflare_account_id,
            "CLOUDFLARE_AI_API_TOKEN": self.cloudflare_ai_api_token,
        }
        return [name for name, value in names.items() if not value]


def load_llm_settings() -> LlmSettings:
    """Load only the Workers AI settings from the environment."""
    return LlmSettings()
