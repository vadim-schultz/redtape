from __future__ import annotations

import uuid

import pytest
from app.features.documents.promotion import DocumentPromotion
from app.features.documents.repository import DocumentRepository
from app.features.events.repository import EventLogRepository
from app.features.events.service import EventLogService
from app.features.suggestions.repository import SuggestionRepository
from app.features.suggestions.service import AlreadyDecidedError, SuggestionService
from app.features.taxonomy.repository import TaxonomyRepository
from app.features.taxonomy.service import TaxonomyService
from app.features.voting.repository import VoteRepository
from app.features.voting.service import NotFoundError, SelfVoteError, SuggestionNotVotableError, VoteService
from app.models.document import Document
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.suggestion import Suggestion, SuggestionKind, SuggestionSource, SuggestionStatus
from app.models.suggestion_event import EventType
from app.models.suggestion_vote import SuggestionVote
from app.models.user import AppUser
from sqlalchemy import select
from sqlalchemy.orm import Session

from suggestion_support import compose_suggestion_service


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
        payload={"title_i18n": {"en": "Residency permit"}, "official_url": "https://example.gov/residency"},
    )
    session.add(row)
    session.flush()
    return row


@pytest.fixture
def pending_suggestion(db_session: Session, jurisdiction: Jurisdiction, submitter: AppUser) -> Suggestion:
    return _suggestion(db_session, jurisdiction, submitter)


@pytest.fixture
def event_log_service(db_session: Session) -> EventLogService:
    return EventLogService(EventLogRepository(db_session))


@pytest.fixture
def suggestion_service(db_session: Session, event_log_service: EventLogService) -> SuggestionService:
    documents = DocumentPromotion(DocumentRepository(db_session), TaxonomyService(TaxonomyRepository(db_session)))
    taxonomy = TaxonomyService(TaxonomyRepository(db_session))
    return compose_suggestion_service(SuggestionRepository(db_session), documents, taxonomy, event_log_service)


@pytest.fixture
def service(
    db_session: Session, suggestion_service: SuggestionService, event_log_service: EventLogService
) -> VoteService:
    return VoteService(VoteRepository(db_session), suggestion_service, event_log_service)


def _vote(session: Session, suggestion_id: uuid.UUID, user_id: uuid.UUID) -> SuggestionVote | None:
    return session.scalar(
        select(SuggestionVote).where(SuggestionVote.suggestion_id == suggestion_id, SuggestionVote.user_id == user_id)
    )


def _voters(db_session: Session, n: int) -> list[AppUser]:
    users = [AppUser(id=uuid.uuid4(), email=f"{uuid.uuid4().hex}@example.com") for _ in range(n)]
    db_session.add_all(users)
    db_session.flush()
    return users


def _document_by_slug(session: Session, jurisdiction: Jurisdiction, slug: str) -> Document | None:
    return session.scalar(select(Document).where(Document.jurisdiction_id == jurisdiction.id, Document.slug == slug))


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


def test_cast_a_vote_that_reaches_the_approve_threshold_moves_the_suggestion_to_approved(
    db_session: Session, service: VoteService, pending_suggestion: Suggestion
) -> None:
    for voter in _voters(db_session, 3):
        service.cast(suggestion_id=pending_suggestion.id, user_id=voter.id, value=1)

    assert pending_suggestion.status == SuggestionStatus.APPROVED


def test_cast_a_vote_that_reaches_the_reject_threshold_moves_the_suggestion_to_rejected(
    db_session: Session, service: VoteService, pending_suggestion: Suggestion
) -> None:
    for voter in _voters(db_session, 3):
        service.cast(suggestion_id=pending_suggestion.id, user_id=voter.id, value=-1)

    assert pending_suggestion.status == SuggestionStatus.REJECTED


def test_cast_a_vote_that_does_not_cross_a_threshold_leaves_the_suggestion_pending(
    db_session: Session, service: VoteService, pending_suggestion: Suggestion
) -> None:
    for voter in _voters(db_session, 2):
        service.cast(suggestion_id=pending_suggestion.id, user_id=voter.id, value=1)

    assert pending_suggestion.status == SuggestionStatus.PENDING


def test_cast_once_approved_a_later_vote_from_a_different_user_is_rejected_as_not_votable(
    db_session: Session, service: VoteService, pending_suggestion: Suggestion
) -> None:
    voters = _voters(db_session, 4)
    for voter in voters[:3]:
        service.cast(suggestion_id=pending_suggestion.id, user_id=voter.id, value=1)
    assert pending_suggestion.status == SuggestionStatus.APPROVED

    with pytest.raises(SuggestionNotVotableError):
        service.cast(suggestion_id=pending_suggestion.id, user_id=voters[3].id, value=1)


def test_cast_logs_a_voted_event_with_the_value_and_the_voter(
    service: VoteService, event_log_service: EventLogService, pending_suggestion: Suggestion, voter: AppUser
) -> None:
    service.cast(suggestion_id=pending_suggestion.id, user_id=voter.id, value=1)

    events = event_log_service.list_for(pending_suggestion.id)
    voted = [e for e in events if e.event_type == EventType.VOTED]
    assert len(voted) == 1
    assert voted[0].data == {"value": 1}
    assert voted[0].actor_user_id == voter.id


def test_remove_after_a_decision_is_rejected_and_changes_nothing(
    db_session: Session, service: VoteService, pending_suggestion: Suggestion
) -> None:
    voters = _voters(db_session, 3)
    for voter in voters:
        service.cast(suggestion_id=pending_suggestion.id, user_id=voter.id, value=1)
    assert pending_suggestion.status == SuggestionStatus.APPROVED

    with pytest.raises(SuggestionNotVotableError):
        service.remove(suggestion_id=pending_suggestion.id, user_id=voters[0].id)

    assert pending_suggestion.status == SuggestionStatus.APPROVED
    assert _vote(db_session, pending_suggestion.id, voters[0].id) is not None


def test_remove_on_a_rejected_suggestion_is_rejected_and_keeps_the_vote(
    db_session: Session, service: VoteService, pending_suggestion: Suggestion
) -> None:
    voters = _voters(db_session, 3)
    for voter in voters:
        service.cast(suggestion_id=pending_suggestion.id, user_id=voter.id, value=-1)
    assert pending_suggestion.status == SuggestionStatus.REJECTED

    with pytest.raises(SuggestionNotVotableError):
        service.remove(suggestion_id=pending_suggestion.id, user_id=voters[0].id)

    assert pending_suggestion.status == SuggestionStatus.REJECTED
    assert _vote(db_session, pending_suggestion.id, voters[0].id) is not None


def test_remove_on_an_unknown_suggestion_raises_not_found(service: VoteService, voter: AppUser) -> None:
    with pytest.raises(NotFoundError):
        service.remove(suggestion_id=uuid.uuid4(), user_id=voter.id)


def test_cast_that_hits_a_promotion_conflict_keeps_the_vote_and_leaves_the_suggestion_pending(
    db_session: Session,
    service: VoteService,
    suggestion_service: SuggestionService,
    event_log_service: EventLogService,
    jurisdiction: Jurisdiction,
    submitter: AppUser,
) -> None:
    first = _suggestion(db_session, jurisdiction, submitter)
    second = _suggestion(db_session, jurisdiction, submitter)
    suggestion_service.transition_to(first.id, SuggestionStatus.APPROVED, actor=None)

    voters = _voters(db_session, 3)
    for voter in voters[:2]:
        service.cast(suggestion_id=second.id, user_id=voter.id, value=1)
    result = service.cast(suggestion_id=second.id, user_id=voters[2].id, value=1)

    assert result.promotion_blocked is not None
    assert "residency-permit" in result.promotion_blocked
    assert _vote(db_session, second.id, voters[2].id) is not None
    assert second.status == SuggestionStatus.PENDING
    events = event_log_service.list_for(second.id)
    assert len([e for e in events if e.event_type == EventType.VOTED]) == 3
    assert not any(e.event_type in (EventType.PROMOTED, EventType.STATUS_CHANGED) for e in events)


def test_cast_without_a_conflict_reports_nothing_blocked(
    db_session: Session, service: VoteService, jurisdiction: Jurisdiction, submitter: AppUser
) -> None:
    other_jurisdiction = Jurisdiction(
        kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Otherland"}, code=f"O{uuid.uuid4().hex[:8]}"
    )
    db_session.add(other_jurisdiction)
    db_session.flush()
    promotes = _suggestion(db_session, jurisdiction, submitter)
    stays_pending = _suggestion(db_session, other_jurisdiction, submitter)
    voters = _voters(db_session, 3)

    result = None
    for voter in voters:
        result = service.cast(suggestion_id=promotes.id, user_id=voter.id, value=1)
    assert result is not None
    assert result.promotion_blocked is None
    assert promotes.status == SuggestionStatus.APPROVED

    sub_threshold_result = service.cast(suggestion_id=stays_pending.id, user_id=voters[0].id, value=1)
    assert sub_threshold_result.promotion_blocked is None
    assert stays_pending.status == SuggestionStatus.PENDING


def test_a_blocked_promotion_is_retried_by_the_next_vote(
    db_session: Session,
    service: VoteService,
    suggestion_service: SuggestionService,
    jurisdiction: Jurisdiction,
    submitter: AppUser,
) -> None:
    first = _suggestion(db_session, jurisdiction, submitter)
    second = _suggestion(db_session, jurisdiction, submitter)
    suggestion_service.transition_to(first.id, SuggestionStatus.APPROVED, actor=None)

    voters = _voters(db_session, 4)
    for voter in voters[:3]:
        service.cast(suggestion_id=second.id, user_id=voter.id, value=1)
    assert second.status == SuggestionStatus.PENDING

    competing_document = _document_by_slug(db_session, jurisdiction, "residency-permit")
    assert competing_document is not None
    db_session.delete(competing_document)
    db_session.flush()

    result = service.cast(suggestion_id=second.id, user_id=voters[3].id, value=1)

    assert result.promotion_blocked is None
    assert second.status == SuggestionStatus.APPROVED
    assert _document_by_slug(db_session, jurisdiction, "residency-permit") is not None


def test_cast_propagates_already_decided_when_the_suggestion_was_decided_behind_its_back(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
    service: VoteService,
    suggestion_service: SuggestionService,
    pending_suggestion: Suggestion,
) -> None:
    voters = _voters(db_session, 3)
    for voter in voters[:2]:
        service.cast(suggestion_id=pending_suggestion.id, user_id=voter.id, value=1)

    def _raise(*args: object, **kwargs: object) -> Suggestion:
        raise AlreadyDecidedError("decided behind our back")

    monkeypatch.setattr(suggestion_service, "transition_to", _raise)

    with pytest.raises(AlreadyDecidedError):
        service.cast(suggestion_id=pending_suggestion.id, user_id=voters[2].id, value=1)
