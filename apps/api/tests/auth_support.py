"""Test helpers for the authentication dependencies."""

from __future__ import annotations

import pytest
from app.features.auth import dependencies as auth_dependencies
from app.features.auth.jwt import JwtVerifier


def use_jwt_verifier(monkeypatch: pytest.MonkeyPatch, verifier: JwtVerifier) -> None:
    """Make every request verify its bearer token with ``verifier`` for the rest of the test."""
    monkeypatch.setattr(auth_dependencies, "default_jwt_verifier", lambda: verifier)
