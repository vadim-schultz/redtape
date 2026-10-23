"""Ingest settings: the bot identity is read once from the environment."""

from __future__ import annotations

import pytest
from discovery_ingest.config import load_ingest_settings


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCOVERY_API_URL", "https://redtape.test")
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")
    monkeypatch.delenv("BOT_CONTACT_URL", raising=False)


def test_settings_default_the_bot_contact_url_to_the_repository() -> None:
    """settings · bot contact url defaults to the repository url."""
    settings = load_ingest_settings()

    assert settings.bot_contact_url == "https://github.com/vadim-schultz/redtape"
    assert settings.user_agent == "RedtapeBot/1.0 (+https://github.com/vadim-schultz/redtape)"


def test_settings_read_the_bot_contact_url_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """settings · bot contact url comes from BOT_CONTACT_URL."""
    monkeypatch.setenv("BOT_CONTACT_URL", "https://ops.example/bot")

    assert load_ingest_settings().user_agent == "RedtapeBot/1.0 (+https://ops.example/bot)"
