"""Settings for discovery admin allowlist and feature flag."""

from __future__ import annotations

from app.config import Settings


def test_discovery_enabled_is_false_when_allowlist_empty() -> None:
    settings = Settings(_env_file=None, discovery_admin_emails="")

    assert settings.discovery_enabled is False
    assert settings.discovery_admin_email_set == frozenset()


def test_discovery_admin_emails_parsed_lowercase_and_trimmed() -> None:
    settings = Settings(
        _env_file=None,
        discovery_admin_emails=" Admin@Example.com ,ops@rsint.net ,",
    )

    assert settings.discovery_admin_email_set == frozenset({"admin@example.com", "ops@rsint.net"})
    assert settings.discovery_enabled is True


def test_discovery_enabled_when_machine_opt_in_even_without_allowlist() -> None:
    settings = Settings(_env_file=None, discovery_admin_emails="", discovery_machine_opt_in=True)

    assert settings.discovery_enabled is True
