from __future__ import annotations

from app.config import Settings


def test_auth_enabled_is_false_when_nothing_is_configured() -> None:
    settings = Settings(_env_file=None)

    assert settings.auth_enabled is False


def test_auth_enabled_is_true_when_jwks_url_and_issuer_are_set() -> None:
    settings = Settings(
        _env_file=None,
        supabase_jwks_url="https://example.supabase.co/auth/v1/.well-known/jwks.json",
        supabase_jwt_issuer="https://example.supabase.co/auth/v1",
    )

    assert settings.auth_enabled is True


def test_auth_enabled_is_false_when_only_the_issuer_is_set() -> None:
    settings = Settings(_env_file=None, supabase_jwt_issuer="https://example.supabase.co/auth/v1")

    assert settings.auth_enabled is False


def test_audience_defaults_to_authenticated() -> None:
    settings = Settings(_env_file=None)

    assert settings.supabase_jwt_audience == "authenticated"


def test_reads_values_from_environment_variables(monkeypatch) -> None:
    monkeypatch.setenv("SUPABASE_JWKS_URL", "https://example.supabase.co/auth/v1/.well-known/jwks.json")
    monkeypatch.setenv("SUPABASE_JWT_ISSUER", "https://example.supabase.co/auth/v1")
    monkeypatch.setenv("SUPABASE_JWT_AUDIENCE", "custom-audience")

    settings = Settings(_env_file=None)

    assert settings.supabase_jwks_url == "https://example.supabase.co/auth/v1/.well-known/jwks.json"
    assert settings.supabase_jwt_issuer == "https://example.supabase.co/auth/v1"
    assert settings.supabase_jwt_audience == "custom-audience"
