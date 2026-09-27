from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from app.features.auth.repository import ApiKeyRepository
from app.features.auth.service import ApiKeyError, ApiKeyService
from app.models.api_key import ApiKey
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def _api_key(key_hash: str = "a" * 64) -> ApiKey:
    return ApiKey(id=uuid.uuid4(), name="crawler-prod", key_hash=key_hash, key_prefix="abcdefgh")


def _service(session: Session) -> ApiKeyService:
    return ApiKeyService(ApiKeyRepository(session))


def test_api_key_rejects_a_duplicate_hash(db_session: Session) -> None:
    db_session.add(_api_key())
    db_session.flush()
    db_session.add(_api_key())

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_issue_returns_a_key_starting_with_rt_(db_session: Session) -> None:
    key = _service(db_session).issue("crawler-prod")

    assert key.startswith("rt_")


def test_issue_stores_only_the_hash_never_the_plaintext(db_session: Session) -> None:
    key = _service(db_session).issue("crawler-prod")

    row = db_session.execute(sa.text("SELECT name, key_hash, key_prefix FROM api_key")).mappings().one()

    assert key not in row.values()


def test_issued_keys_are_unique(db_session: Session) -> None:
    service = _service(db_session)

    first = service.issue("crawler-a")
    second = service.issue("crawler-b")

    assert first != second


def test_verify_accepts_an_issued_key(db_session: Session) -> None:
    service = _service(db_session)
    key = service.issue("crawler-prod")

    record = service.verify(key)

    assert record.name == "crawler-prod"


def test_verify_rejects_an_unknown_key(db_session: Session) -> None:
    with pytest.raises(ApiKeyError):
        _service(db_session).verify("rt_does-not-exist")


def test_verify_rejects_a_revoked_key_with_the_same_error_as_unknown(db_session: Session) -> None:
    service = _service(db_session)
    key = service.issue("crawler-prod")
    record = service.verify(key)
    service.revoke(record.key_prefix)

    with pytest.raises(ApiKeyError) as revoked_exc_info:
        service.verify(key)
    with pytest.raises(ApiKeyError) as unknown_exc_info:
        service.verify("rt_does-not-exist")

    assert type(revoked_exc_info.value) is type(unknown_exc_info.value)


def test_verify_updates_last_used_at_at_most_once_per_minute(db_session: Session) -> None:
    service = _service(db_session)
    key = service.issue("crawler-prod")

    first = service.verify(key)
    first_seen_at = first.last_used_at
    second = service.verify(key)

    assert first_seen_at is not None
    assert second.last_used_at == first_seen_at
