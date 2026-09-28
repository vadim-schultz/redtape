from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from app.models import (
    ApiKey,
    AppUser,
    Jurisdiction,
    JurisdictionKind,
    Suggestion,
    SuggestionKind,
    SuggestionSource,
    SuggestionStatus,
)
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session


def _jurisdiction(session: Session) -> Jurisdiction:
    jurisdiction = Jurisdiction(
        kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Testland"}, code=f"T{uuid.uuid4().hex[:8]}"
    )
    session.add(jurisdiction)
    session.flush()
    return jurisdiction


def _user(session: Session) -> AppUser:
    user = AppUser(id=uuid.uuid4(), email=f"{uuid.uuid4().hex}@example.com")
    session.add(user)
    session.flush()
    return user


def _api_key(session: Session) -> ApiKey:
    key = ApiKey(name="crawler", key_hash=uuid.uuid4().hex, key_prefix=uuid.uuid4().hex[:8])
    session.add(key)
    session.flush()
    return key


def _suggestion(jurisdiction: Jurisdiction, **overrides: object) -> Suggestion:
    defaults: dict[str, object] = {
        "kind": SuggestionKind.NEW_DOCUMENT,
        "source_type": SuggestionSource.HUMAN,
        "jurisdiction_id": jurisdiction.id,
    }
    defaults.update(overrides)
    return Suggestion(**defaults)


def test_suggestion_persists_with_defaults_status_pending_and_generated_id(db_session: Session) -> None:
    jurisdiction = _jurisdiction(db_session)
    user = _user(db_session)
    suggestion = _suggestion(jurisdiction, submitted_by_user_id=user.id)
    db_session.add(suggestion)
    db_session.flush()
    db_session.expire(suggestion)

    assert suggestion.id is not None
    assert suggestion.status == SuggestionStatus.PENDING


def test_human_suggestion_requires_no_api_key(db_session: Session) -> None:
    jurisdiction = _jurisdiction(db_session)
    user = _user(db_session)
    suggestion = _suggestion(jurisdiction, submitted_by_user_id=user.id)
    db_session.add(suggestion)

    db_session.flush()


def test_human_suggestion_with_an_api_key_is_rejected(db_session: Session) -> None:
    jurisdiction = _jurisdiction(db_session)
    user = _user(db_session)
    key = _api_key(db_session)
    suggestion = _suggestion(jurisdiction, submitted_by_user_id=user.id, submitted_by_api_key_id=key.id)
    db_session.add(suggestion)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_crawler_suggestion_with_a_user_id_is_rejected(db_session: Session) -> None:
    jurisdiction = _jurisdiction(db_session)
    user = _user(db_session)
    suggestion = _suggestion(jurisdiction, source_type=SuggestionSource.CRAWLER, submitted_by_user_id=user.id)
    db_session.add(suggestion)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_deleting_the_submitting_user_keeps_the_suggestion(db_session: Session) -> None:
    jurisdiction = _jurisdiction(db_session)
    user = _user(db_session)
    suggestion = _suggestion(jurisdiction, submitted_by_user_id=user.id)
    db_session.add(suggestion)
    db_session.flush()
    suggestion_id = suggestion.id

    db_session.execute(sa.delete(AppUser).where(AppUser.id == user.id))
    db_session.expire_all()

    persisted = db_session.get(Suggestion, suggestion_id)
    assert persisted is not None
    assert persisted.submitted_by_user_id is None


def test_same_api_key_and_idempotency_key_twice_is_rejected(db_session: Session) -> None:
    jurisdiction = _jurisdiction(db_session)
    key = _api_key(db_session)
    db_session.add(
        _suggestion(
            jurisdiction, source_type=SuggestionSource.CRAWLER, submitted_by_api_key_id=key.id, idempotency_key="abc"
        )
    )
    db_session.flush()
    db_session.add(
        _suggestion(
            jurisdiction, source_type=SuggestionSource.CRAWLER, submitted_by_api_key_id=key.id, idempotency_key="abc"
        )
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_same_idempotency_key_from_two_different_api_keys_is_allowed(db_session: Session) -> None:
    jurisdiction = _jurisdiction(db_session)
    key_a, key_b = _api_key(db_session), _api_key(db_session)
    db_session.add(
        _suggestion(
            jurisdiction, source_type=SuggestionSource.CRAWLER, submitted_by_api_key_id=key_a.id, idempotency_key="abc"
        )
    )
    db_session.add(
        _suggestion(
            jurisdiction, source_type=SuggestionSource.CRAWLER, submitted_by_api_key_id=key_b.id, idempotency_key="abc"
        )
    )

    db_session.flush()


def test_two_human_suggestions_without_keys_do_not_collide(db_session: Session) -> None:
    jurisdiction = _jurisdiction(db_session)
    user_a, user_b = _user(db_session), _user(db_session)
    db_session.add(_suggestion(jurisdiction, submitted_by_user_id=user_a.id))
    db_session.add(_suggestion(jurisdiction, submitted_by_user_id=user_b.id))

    db_session.flush()


def test_unknown_kind_or_status_is_rejected(db_session: Session) -> None:
    jurisdiction = _jurisdiction(db_session)

    with pytest.raises(DBAPIError):
        db_session.execute(
            sa.text(
                "INSERT INTO suggestion (id, kind, status, source_type, jurisdiction_id)"
                " VALUES (:id, 'bogus', 'pending', 'human', :jurisdiction_id)"
            ),
            {"id": str(uuid.uuid4()), "jurisdiction_id": str(jurisdiction.id)},
        )


def test_payload_defaults_to_an_empty_object(db_session: Session) -> None:
    jurisdiction = _jurisdiction(db_session)
    user = _user(db_session)
    suggestion = _suggestion(jurisdiction, submitted_by_user_id=user.id)
    db_session.add(suggestion)
    db_session.flush()
    db_session.expire(suggestion)

    assert suggestion.payload == {}
