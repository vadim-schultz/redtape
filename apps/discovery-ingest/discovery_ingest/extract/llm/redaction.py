"""Replace the Workers AI credentials in anything a command prints or writes."""

from __future__ import annotations

from discovery_ingest.llm_settings import LlmSettings

REDACTED = "<redacted>"


def secrets_of(settings: LlmSettings) -> list[str]:
    """Return the token and the account id that are set."""
    token = settings.cloudflare_ai_api_token
    values = (settings.cloudflare_account_id, token.get_secret_value() if token else None)
    return [value for value in values if value]


def scrub(text: str, secrets: list[str]) -> str:
    """Return ``text`` with every secret replaced by ``<redacted>``."""
    for secret in secrets:
        text = text.replace(secret, REDACTED)
    return text
