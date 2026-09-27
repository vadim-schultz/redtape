from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from app.models import AppUser, UserRole
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session


def _user(email: str = "ada@example.com") -> AppUser:
    return AppUser(id=uuid.uuid4(), email=email)


def test_app_user_persists_with_the_supplied_id_and_default_role_user(db_session: Session) -> None:
    user_id = uuid.uuid4()
    user = AppUser(id=user_id, email="ada@example.com")
    db_session.add(user)
    db_session.flush()
    db_session.expire(user)

    assert user.id == user_id
    assert user.email == "ada@example.com"
    assert user.role == UserRole.USER


def test_app_user_rejects_a_duplicate_email(db_session: Session) -> None:
    db_session.add(_user("ada@example.com"))
    db_session.flush()
    db_session.add(_user("ada@example.com"))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_app_user_rejects_an_email_differing_only_in_case(db_session: Session) -> None:
    db_session.add(_user("ada@example.com"))
    db_session.flush()
    db_session.add(_user("Ada@Example.com"))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_app_user_rejects_an_unknown_role_value(db_session: Session) -> None:
    with pytest.raises(DBAPIError):
        db_session.execute(
            sa.text("INSERT INTO app_user (id, email, role) VALUES (:id, :email, 'bogus')"),
            {"id": str(uuid.uuid4()), "email": "unknown-role@example.com"},
        )


def test_app_user_created_at_is_set_by_the_database(db_session: Session) -> None:
    user = _user()
    db_session.add(user)
    db_session.flush()
    db_session.expire(user)

    assert user.created_at is not None
