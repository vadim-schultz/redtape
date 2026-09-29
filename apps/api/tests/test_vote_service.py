from __future__ import annotations

import uuid

import pytest
from app.features.documents.repository import DocumentRepository
from app.features.documents.service import DocumentService
from app.features.suggestions.repository import SuggestionRepository
from app.features.suggestions.service import SuggestionService
from app.features.taxonomy.repository import TaxonomyRepository
from app.features.taxonomy.service import TaxonomyService
from app.features.voting.repository import VoteRepository
from app.features.voting.service import NotFoundError, SelfVoteError, SuggestionNotVotableError, VoteService
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.suggestion import Suggestion, SuggestionKind, SuggestionSource, SuggestionStatus
from app.models.suggestion_vote import SuggestionVote
from app.models.user import AppUser
from sqlalchemy import select
from sqlalchemy.orm import Session


@pytest.fixture
def jurisdiction(db_session: Session) -> Jurisdiction:
    row = Jurisdiction(kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Testland"}, code=f"T{uuid.uuid4().hex[:8]}")
    db_session.add(row)
    db_session.flush()
    return row


@pytest.fixture
def submitter(db_session: Session) -> AppUser:
    row = AppUser(id=uuid.uuid4(), email=f"{uuid.uuid4().hex}@example.com")
    db_session.add(row)
    db_session.flush()
    return row


@pytest.fixture
def voter(db_session: Session) -> AppUser:
    row = AppUser(id=uuid.uuid4(), email=f"{uuid.uuid4().hex}@example.com")
    db_session.add(row)
    db_session.flush()
    return row


def _suggestion(
    session: Session,
    jurisdiction: Jurisdiction,
    submitter: AppUser,
    status: SuggestionStatus = SuggestionStatus.PENDING,
) -> Suggestion:
    row = Suggestion(
        kind=SuggestionKind.NEW_DOCUMENT,
        status=status,
        source_type=SuggestionSource.HUMAN,
        jurisdiction_id=jurisdiction.id,
        submitted_by_user_id=submitter.id,
    )
    session.add(row)
    session.flush()
    return row


@pytest.fixture
def pending_suggestion(db_session: Session, jurisdiction: Jurisdiction, submitter: AppUser) -> Suggestion:
    return _suggestion(db_session, jurisdiction, submitter)


@pytest.fixture
def suggestion_service(db_session: Session) -> SuggestionService:
    documents = DocumentService(DocumentRepository(db_session), TaxonomyService(TaxonomyRepository(db_session)))
    taxonomy = TaxonomyService(TaxonomyRepository(db_session))
    return SuggestionService(SuggestionRepository(db_session), documents, taxonomy)


@pytest.fixture
def service(db_session: Session, suggestion_service: SuggestionService) -> VoteService:
    return VoteService(VoteRepository(db_session), suggestion_service)


def _vote(session: Session, suggestion_id: uuid.UUID, user_id: uuid.UUID) -> SuggestionVote | None:
    return session.scalar(
        select(SuggestionVote).where(SuggestionVote.suggestion_id == suggestion_id, SuggestionVote.user_id == user_id)
    )


def test_cast_records_an_up_vote_for_a_pending_suggestion(
    db_session: Session, service: VoteService, pending_suggestion: Suggestion, voter: AppUser
) -> None:
    service.cast(suggestion_id=pending_suggestion.id, user_id=voter.id, value=1)

    vote = _vote(db_session, pending_suggestion.id, voter.id)
    assert vote is not None
    assert vote.value == 1


def test_cast_changes_an_existing_votes_value(
    db_session: Session, service: VoteService, pending_suggestion: Suggestion, voter: AppUser
) -> None:
    service.cast(suggestion_id=pending_suggestion.id, user_id=voter.id, value=1)

    service.cast(suggestion_id=pending_suggestion.id, user_id=voter.id, value=-1)

    rows = db_session.scalars(
        select(SuggestionVote).where(
            SuggestionVote.suggestion_id == pending_suggestion.id, SuggestionVote.user_id == voter.id
        )
    ).all()
    assert len(rows) == 1
    assert rows[0].value == -1


def test_cast_the_same_value_twice_is_a_no_op(
    db_session: Session, service: VoteService, pending_suggestion: Suggestion, voter: AppUser
) -> None:
    service.cast(suggestion_id=pending_suggestion.id, user_id=voter.id, value=1)

    service.cast(suggestion_id=pending_suggestion.id, user_id=voter.id, value=1)

    rows = db_session.scalars(
        select(SuggestionVote).where(
            SuggestionVote.suggestion_id == pending_suggestion.id, SuggestionVote.user_id == voter.id
        )
    ).all()
    assert len(rows) == 1
    assert rows[0].value == 1


def test_cast_rejects_voting_on_the_callers_own_suggestion(
    service: VoteService, pending_suggestion: Suggestion, submitter: AppUser
) -> None:
    with pytest.raises(SelfVoteError):
        service.cast(suggestion_id=pending_suggestion.id, user_id=submitter.id, value=1)


def test_cast_rejects_voting_on_an_approved_suggestion(
    db_session: Session, service: VoteService, jurisdiction: Jurisdiction, submitter: AppUser, voter: AppUser
) -> None:
    suggestion = _suggestion(db_session, jurisdiction, submitter, status=SuggestionStatus.APPROVED)

    with pytest.raises(SuggestionNotVotableError):
        service.cast(suggestion_id=suggestion.id, user_id=voter.id, value=1)


def test_cast_rejects_voting_on_a_rejected_suggestion(
    db_session: Session, service: VoteService, jurisdiction: Jurisdiction, submitter: AppUser, voter: AppUser
) -> None:
    suggestion = _suggestion(db_session, jurisdiction, submitter, status=SuggestionStatus.REJECTED)

    with pytest.raises(SuggestionNotVotableError):
        service.cast(suggestion_id=suggestion.id, user_id=voter.id, value=1)


def test_cast_rejects_an_unknown_suggestion(service: VoteService, voter: AppUser) -> None:
    with pytest.raises(NotFoundError):
        service.cast(suggestion_id=uuid.uuid4(), user_id=voter.id, value=1)


def test_remove_deletes_an_existing_vote(
    db_session: Session, service: VoteService, pending_suggestion: Suggestion, voter: AppUser
) -> None:
    service.cast(suggestion_id=pending_suggestion.id, user_id=voter.id, value=1)

    service.remove(suggestion_id=pending_suggestion.id, user_id=voter.id)

    assert _vote(db_session, pending_suggestion.id, voter.id) is None


def test_remove_is_a_no_op_when_there_is_no_vote(
    service: VoteService, pending_suggestion: Suggestion, voter: AppUser
) -> None:
    service.remove(suggestion_id=pending_suggestion.id, user_id=voter.id)
