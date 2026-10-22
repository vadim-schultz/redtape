"""Shared guard session helper, split discovery admin guards and the precise principal type."""

from __future__ import annotations

from typing import Any, get_args, get_type_hints
from unittest.mock import MagicMock

import pytest
from app.config import settings
from app.features.auth import guard_session as guard_session_module
from app.features.auth.guard_session import guard_session
from app.features.auth.principal import Principal
from app.features.discovery.guards import require_auth_enabled, require_discovery_enabled
from app.features.suggestions.submission import provide_submission
from litestar.exceptions import NotAuthorizedException, ServiceUnavailableException


@pytest.fixture
def fake_session(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    session = MagicMock()
    session.__enter__.return_value = session
    monkeypatch.setattr(guard_session_module, "SessionLocal", lambda: session)
    return session


def test_guard_session_commits_then_closes_on_success(fake_session: MagicMock) -> None:
    with guard_session() as session:
        assert session is fake_session

    fake_session.commit.assert_called_once_with()
    fake_session.__exit__.assert_called_once()


def test_guard_session_closes_without_committing_on_error(fake_session: MagicMock) -> None:
    with pytest.raises(RuntimeError), guard_session():
        raise RuntimeError("boom")

    fake_session.commit.assert_not_called()
    fake_session.__exit__.assert_called_once()


def test_discovery_enabled_guard_passes_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "discovery_admin_emails", "a@example.com")

    require_discovery_enabled(MagicMock(), MagicMock())


def test_discovery_enabled_guard_raises_503_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "discovery_admin_emails", "")
    monkeypatch.setattr(settings, "discovery_machine_opt_in", False)

    with pytest.raises(ServiceUnavailableException):
        require_discovery_enabled(MagicMock(), MagicMock())


def test_auth_enabled_guard_passes_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "supabase_jwks_url", "https://example.supabase.co/jwks.json")
    monkeypatch.setattr(settings, "supabase_jwt_issuer", "https://example.supabase.co/auth/v1")

    require_auth_enabled(MagicMock(), MagicMock())


def test_auth_enabled_guard_raises_401_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "supabase_jwks_url", None)

    with pytest.raises(NotAuthorizedException):
        require_auth_enabled(MagicMock(), MagicMock())


def test_submission_principal_has_the_precise_type() -> None:
    hints: dict[str, Any] = get_type_hints(provide_submission, include_extras=True)

    assert get_args(hints["principal"])[0] == Principal
