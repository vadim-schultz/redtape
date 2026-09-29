"""Tests for `VoteRepository.tally_for` and `tally_for_many` (Chapter 4)."""

from __future__ import annotations

import uuid
from collections.abc import Generator
from contextlib import contextmanager
from uuid import UUID

import pytest
from app.features.voting.repository import VoteRepository
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.suggestion import Suggestion, SuggestionKind, SuggestionSource, SuggestionStatus
from app.models.suggestion_vote import SuggestionVote
from app.models.user import AppUser
from sqlalchemy import event
from sqlalchemy.orm import Session


@pytest.fixture
def jurisdiction(db_session: Session) -> Jurisdiction:
    row = Jurisdiction(kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Testland"}, code=f"T{uuid.uuid4().hex[:8]}")
    db_session.add(row)
    db_session.flush()
    return row


@pytest.fixture
def repository(db_session: Session) -> VoteRepository:
    return VoteRepository(db_session)


def _user(db_session: Session) -> AppUser:
    row = AppUser(id=uuid.uuid4(), email=f"{uuid.uuid4().hex}@example.com")
    db_session.add(row)
    db_session.flush()
    return row


def _suggestion(db_session: Session, jurisdiction: Jurisdiction) -> Suggestion:
    row = Suggestion(
        kind=SuggestionKind.NEW_DOCUMENT,
        status=SuggestionStatus.PENDING,
        source_type=SuggestionSource.HUMAN,
        jurisdiction_id=jurisdiction.id,
        submitted_by_user_id=_user(db_session).id,
    )
    db_session.add(row)
    db_session.flush()
    return row


def _vote(db_session: Session, suggestion_id: UUID, user_id: UUID, value: int) -> None:
    db_session.add(SuggestionVote(suggestion_id=suggestion_id, user_id=user_id, value=value))
    db_session.flush()


@contextmanager
def _count_queries(db_session: Session) -> Generator[dict[str, int], None, None]:
    counter = {"n": 0}
    connection = db_session.connection()

    def _before_cursor_execute(*_args: object, **_kwargs: object) -> None:
        counter["n"] += 1

    event.listen(connection, "before_cursor_execute", _before_cursor_execute)
    try:
        yield counter
    finally:
        event.remove(connection, "before_cursor_execute", _before_cursor_execute)


def test_tally_for_counts_up_and_down_votes_and_computes_score(
    db_session: Session, repository: VoteRepository, jurisdiction: Jurisdiction
) -> None:
    suggestion = _suggestion(db_session, jurisdiction)
    _vote(db_session, suggestion.id, _user(db_session).id, 1)
    _vote(db_session, suggestion.id, _user(db_session).id, 1)
    _vote(db_session, suggestion.id, _user(db_session).id, -1)

    tally = repository.tally_for(suggestion.id)

    assert (tally.up, tally.down, tally.score) == (2, 1, 1)


def test_tally_for_a_suggestion_with_no_votes_has_zeros(
    db_session: Session, repository: VoteRepository, jurisdiction: Jurisdiction
) -> None:
    suggestion = _suggestion(db_session, jurisdiction)

    tally = repository.tally_for(suggestion.id)

    assert (tally.up, tally.down, tally.score) == (0, 0, 0)


def test_tally_for_many_returns_one_querys_worth_of_tallies_for_a_page_of_ids(
    db_session: Session, repository: VoteRepository, jurisdiction: Jurisdiction
) -> None:
    suggestions = [_suggestion(db_session, jurisdiction) for _ in range(5)]
    for suggestion in suggestions:
        _vote(db_session, suggestion.id, _user(db_session).id, 1)

    with _count_queries(db_session) as counter:
        tallies = repository.tally_for_many([s.id for s in suggestions])

    assert counter["n"] == 1
    assert {sid: (t.up, t.down, t.score) for sid, t in tallies.items()} == {s.id: (1, 0, 1) for s in suggestions}
