from __future__ import annotations

from app.config import settings
from app.middleware.cors import build_cors_config


def test_allow_origins_matches_configured_origins_exactly(monkeypatch) -> None:
    monkeypatch.setattr(settings, "cors_allowed_origins", "https://a.example.com,https://b.example.com")

    cors_config = build_cors_config()

    assert cors_config.allow_origins == ["https://a.example.com", "https://b.example.com"]


def test_allow_origins_falls_back_to_localhost_when_unset(monkeypatch) -> None:
    monkeypatch.setattr(settings, "cors_allowed_origins", "")

    cors_config = build_cors_config()

    assert cors_config.allow_origins == ["http://localhost:5173"]
