from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
import scripts.set_user_role as set_user_role_script
from app.features.auth.repository import UserRepository
from app.features.auth.service import UnknownRoleError, UnknownUserError, UserService
from app.models import AppUser
from app.models.user import UserRole
from scripts.set_user_role import main
from sqlalchemy.orm import Session


def _seeded_user(session: Session, email: str = "ada@example.com", role: UserRole = UserRole.USER) -> AppUser:
    user = AppUser(id=uuid.uuid4(), email=email, display_name="Ada", role=role)
    session.add(user)
    session.flush()
    return user


@contextmanager
def _keep_open(session: Session) -> Iterator[Session]:
    """Stand in for `SessionLocal()`: hands the script the fixture's session without closing it."""

    yield session


def test_set_role_updates_the_stored_role(db_session: Session) -> None:
    user = _seeded_user(db_session)
    service = UserService(UserRepository(db_session))

    updated = service.set_role(user.email, "moderator")

    assert updated.id == user.id
    assert updated.role == UserRole.MODERATOR


def test_set_role_unknown_email_raises(db_session: Session) -> None:
    service = UserService(UserRepository(db_session))

    with pytest.raises(UnknownUserError):
        service.set_role("ghost@example.com", "moderator")


def test_set_role_unknown_role_raises(db_session: Session) -> None:
    user = _seeded_user(db_session)
    service = UserService(UserRepository(db_session))

    with pytest.raises(UnknownRoleError):
        service.set_role(user.email, "superadmin")


@pytest.fixture(autouse=True)
def _use_test_session(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(set_user_role_script, "SessionLocal", lambda: _keep_open(db_session))


def test_script_rejects_an_unknown_role_name(
    db_session: Session, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    user = _seeded_user(db_session)
    monkeypatch.setattr(sys, "argv", ["set_user_role.py", user.email, "superadmin"])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code != 0
    err = capsys.readouterr().err
    assert "user" in err and "moderator" in err and "admin" in err


def test_script_rejects_an_unknown_email(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["set_user_role.py", "ghost@example.com", "moderator"])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code != 0


def test_script_is_idempotent(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    user = _seeded_user(db_session)
    monkeypatch.setattr(sys, "argv", ["set_user_role.py", user.email, "moderator"])

    main()
    main()

    db_session.refresh(user)
    assert user.role == UserRole.MODERATOR
