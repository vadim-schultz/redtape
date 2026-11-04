"""Settings layering · one Cloudflare account declaration, bot identity without secrets, no os.environ outside config."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from discovery_ingest.cli import main
from discovery_ingest.config import (
    DEFAULT_FIM_PORTAL_URL,
    BotSettings,
    BrowserSettings,
    IngestSettings,
    load_bot_settings,
)
from discovery_ingest.llm_settings import LlmSettings
from discovery_ingest.operations import probes

PACKAGE = Path(__file__).parents[1] / "discovery_ingest"
ENVIRON_ALLOWED = {PACKAGE / "config.py", PACKAGE / "llm_settings.py", PACKAGE / "cloudflare_account_settings.py"}


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCOVERY_API_URL", "https://redtape.test")
    monkeypatch.setenv("DISCOVERY_API_KEY", "test-machine-key")
    monkeypatch.delenv("BOT_CONTACT_URL", raising=False)
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)


def test_settings_declare_cloudflare_account_id_once() -> None:
    """settings · the account id is declared by the shared base only, and reaches every settings class."""
    assert "cloudflare_account_id" not in BrowserSettings.__dict__.get("__annotations__", {})
    assert "cloudflare_account_id" not in LlmSettings.__dict__.get("__annotations__", {})
    assert "cloudflare_account_id" in IngestSettings.model_fields
    assert IngestSettings.model_fields["cloudflare_account_id"].validation_alias == "CLOUDFLARE_ACCOUNT_ID"


def test_bot_settings_are_inherited_by_ingest_settings() -> None:
    """settings · IngestSettings is a BotSettings, so the bot identity has one declaration."""
    assert issubclass(IngestSettings, BotSettings)
    assert "bot_contact_url" not in IngestSettings.__dict__.get("__annotations__", {})


def test_bot_settings_default_the_contact_url_and_need_no_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """load_bot_settings · defaults the contact url and succeeds without any Cloudflare or API variable."""
    monkeypatch.delenv("DISCOVERY_API_URL")
    monkeypatch.delenv("DISCOVERY_API_KEY")
    settings = load_bot_settings()

    assert settings.user_agent == "RedtapeBot/1.0 (+https://github.com/vadim-schultz/redtape)"


def test_default_fim_portal_url_is_the_setting_default() -> None:
    """settings · the FIM base URL default is the one constant."""
    assert (
        IngestSettings.model_fields["fim_portal_base_url"].default == DEFAULT_FIM_PORTAL_URL == "https://fimportal.de"
    )


def test_no_module_outside_config_reads_os_environ() -> None:
    """package · only config and the Cloudflare settings modules read os.environ."""
    offenders = []
    for path in PACKAGE.rglob("*.py"):
        if path in ENVIRON_ALLOWED:
            continue
        if re.search(r"\bos\.environ\b|\bos\.getenv\b", path.read_text(encoding="utf-8")):
            offenders.append(str(path))
    assert offenders == []


def test_no_fim_portal_url_literal_outside_the_settings_default() -> None:
    """package · the FIM Portal host appears only in the one settings default."""
    offenders = []
    for path in PACKAGE.rglob("*.py"):
        if path == PACKAGE / "config.py":
            continue
        if "fimportal.de" in path.read_text(encoding="utf-8"):
            offenders.append(str(path))
    assert offenders == []


def test_fim_probe_user_agent_comes_from_bot_settings(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """fim probe · the fetcher identifies itself with BOT_CONTACT_URL, and no ingest variable is needed."""
    monkeypatch.delenv("DISCOVERY_API_URL")
    monkeypatch.delenv("DISCOVERY_API_KEY")
    monkeypatch.setenv("BOT_CONTACT_URL", "https://ops.example/bot")
    agents: list[str] = []

    class RecordingFetcher:
        def __init__(self, *, user_agent: str, **_: Any) -> None:
            agents.append(user_agent)

    monkeypatch.setattr("discovery_ingest.operations.probes.PoliteUrlFetcher", RecordingFetcher)
    monkeypatch.setattr("discovery_ingest.operations.probes.probe_keys", lambda *_args: [])
    monkeypatch.setattr("discovery_ingest.operations.probes.probe_lines", lambda _results: [])
    monkeypatch.setattr("discovery_ingest.operations.probes.gate_passed", lambda _results: True)

    assert main(["fim", "probe", "--keys", "99154021000000"]) == 0
    assert agents == ["RedtapeBot/1.0 (+https://ops.example/bot)"]
    assert capsys.readouterr().err == ""


def test_browser_probe_honours_bot_contact_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """browser probe · the probe plan carries the user agent built from BOT_CONTACT_URL."""
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "account")
    monkeypatch.setenv("CLOUDFLARE_BROWSER_API_TOKEN", "token")
    monkeypatch.setenv("BOT_CONTACT_URL", "https://ops.example/bot")
    seen: list[str] = []

    def fake_plan(*_args: Any, user_agent: str, **_kwargs: Any) -> None:
        seen.append(user_agent)
        raise RuntimeError("stop after the plan")

    monkeypatch.setattr(probes, "probe_plan", fake_plan)

    with pytest.raises(RuntimeError, match="stop after the plan"):
        main(["browser", "probe", "--url", "https://portal.example/a"])
    assert seen == ["RedtapeBot/1.0 (+https://ops.example/bot)"]
