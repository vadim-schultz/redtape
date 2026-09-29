from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from app.models import (
    AppUser,
    Jurisdiction,
    JurisdictionKind,
    Suggestion,
    SuggestionKind,
    SuggestionSource,
    SuggestionVote,
)
from sqlalchemy.exc import IntegrityError
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


def _suggestion(session: Session, jurisdiction: Jurisdiction) -> Suggestion:
    suggestion = Suggestion(
        kind=SuggestionKind.NEW_DOCUMENT, source_type=SuggestionSource.CRAWLER, jurisdiction_id=jurisdiction.id
    )
    session.add(suggestion)
    session.flush()
    return suggestion


def test_persists_a_valid_vote(db_session: Session) -> None:
    jurisdiction = _jurisdiction(db_session)
    suggestion = _suggestion(db_session, jurisdiction)
    user = _user(db_session)
    vote = SuggestionVote(suggestion_id=suggestion.id, user_id=user.id, value=1)
    db_session.add(vote)
    db_session.flush()
    db_session.expire(vote)

    assert vote.id is not None
    assert vote.value == 1
    assert vote.created_at is not None


def test_rejects_a_value_other_than_1_or_negative_1(db_session: Session) -> None:
    jurisdiction = _jurisdiction(db_session)
    suggestion = _suggestion(db_session, jurisdiction)
    user = _user(db_session)
    db_session.add(SuggestionVote(suggestion_id=suggestion.id, user_id=user.id, value=2))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_rejects_a_second_row_for_the_same_suggestion_and_user(db_session: Session) -> None:
    jurisdiction = _jurisdiction(db_session)
    suggestion = _suggestion(db_session, jurisdiction)
    user = _user(db_session)
    db_session.add(SuggestionVote(suggestion_id=suggestion.id, user_id=user.id, value=1))
    db_session.flush()
    db_session.add(SuggestionVote(suggestion_id=suggestion.id, user_id=user.id, value=-1))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_allows_the_same_user_to_vote_on_a_different_suggestion(db_session: Session) -> None:
    jurisdiction = _jurisdiction(db_session)
    suggestion_a = _suggestion(db_session, jurisdiction)
    suggestion_b = _suggestion(db_session, jurisdiction)
    user = _user(db_session)
    db_session.add(SuggestionVote(suggestion_id=suggestion_a.id, user_id=user.id, value=1))
    db_session.add(SuggestionVote(suggestion_id=suggestion_b.id, user_id=user.id, value=-1))

    db_session.flush()


def test_deleting_the_suggestion_deletes_its_votes(db_session: Session) -> None:
    jurisdiction = _jurisdiction(db_session)
    suggestion = _suggestion(db_session, jurisdiction)
    user = _user(db_session)
    vote = SuggestionVote(suggestion_id=suggestion.id, user_id=user.id, value=1)
    db_session.add(vote)
    db_session.flush()
    vote_id = vote.id

    db_session.execute(sa.delete(Suggestion).where(Suggestion.id == suggestion.id))
    db_session.expire_all()

    assert db_session.get(SuggestionVote, vote_id) is None


def test_deleting_the_user_deletes_their_votes(db_session: Session) -> None:
    jurisdiction = _jurisdiction(db_session)
    suggestion = _suggestion(db_session, jurisdiction)
    user = _user(db_session)
    vote = SuggestionVote(suggestion_id=suggestion.id, user_id=user.id, value=1)
    db_session.add(vote)
    db_session.flush()
    vote_id = vote.id

    db_session.execute(sa.delete(AppUser).where(AppUser.id == user.id))
    db_session.expire_all()

    assert db_session.get(SuggestionVote, vote_id) is None
