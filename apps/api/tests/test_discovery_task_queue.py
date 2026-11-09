"""Unit tests for the discovery task queue collaborator."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.features.discovery.errors import DiscoveryTaskNotFoundError, TaskNotClaimedError
from app.features.discovery.repository import DiscoveryRepository, TaskTarget
from app.features.discovery.task_queue import TaskQueue
from app.features.discovery.task_retry import BACKOFF, MAX_ATTEMPTS
from app.models.api_key import ApiKey
from app.models.discovery import (
    CatalogueService,
    DiscoveryArtifact,
    DiscoveryArtifactKind,
    DiscoveryCandidateEdge,
    DiscoveryCandidateMention,
    DiscoveryDocumentCandidate,
    DiscoveryEdgeBasis,
    DiscoveryEvent,
    DiscoveryEventType,
    DiscoveryMentionRole,
    DiscoveryTask,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from test_discovery_admin_api import _catalogue


@pytest.fixture
def queue(db_session: Session) -> TaskQueue:
    return TaskQueue(DiscoveryRepository(db_session))


def test_enqueue_for_service_creates_a_pending_task_for_a_portal_url(queue: TaskQueue, db_session: Session) -> None:
    catalogue = _catalogue(db_session)
    catalogue.portal_url = "https://example.gov/portal"

    task = queue.enqueue_for_service(catalogue)

    assert task is not None
    assert task.status == DiscoveryTaskStatus.PENDING
    assert task.target_url == "https://example.gov/portal"


def test_enqueue_for_service_without_portal_url_creates_nothing(queue: TaskQueue, db_session: Session) -> None:
    catalogue = _catalogue(db_session)
    catalogue.portal_url = None

    assert queue.enqueue_for_service(catalogue) is None


def test_claim_pending_leases_enqueued_tasks_to_the_key(queue: TaskQueue, db_session: Session) -> None:
    catalogue = _catalogue(db_session)
    catalogue.portal_url = "https://example.gov/portal"
    queue.enqueue_for_service(catalogue)
    key = ApiKey(name="k", key_hash="h" * 64, key_prefix="p" * 8)
    db_session.add(key)
    db_session.flush()

    claimed = queue.claim_pending(api_key=key, limit=5, now=datetime.now(UTC))

    assert [t.status for t in claimed] == [DiscoveryTaskStatus.CLAIMED]
    assert claimed[0].claimed_by_api_key_id == key.id
    assert claimed[0].lease_expires_at is not None


def test_complete_and_fail_reject_unknown_task_ids(queue: TaskQueue) -> None:
    with pytest.raises(DiscoveryTaskNotFoundError):
        queue.complete(uuid.uuid4())
    with pytest.raises(DiscoveryTaskNotFoundError):
        queue.fail(uuid.uuid4(), "boom", now=datetime.now(UTC))


def _key(db_session: Session) -> ApiKey:
    key = ApiKey(name="k", key_hash=uuid.uuid4().hex * 2, key_prefix="p" * 8)
    db_session.add(key)
    db_session.flush()
    return key


def _seed_task(
    db_session: Session,
    catalogue: CatalogueService,
    kind: DiscoveryTaskKind,
    *,
    path: str,
    priority: int = 100,
    age_minutes: int = 0,
) -> DiscoveryTask:
    target = TaskTarget(catalogue_service_id=catalogue.id, kind=kind, target_url=f"https://example.gov/{path}")
    task = DiscoveryRepository(db_session).insert_task(target, priority=priority)
    task.created_at = datetime.now(UTC) - timedelta(minutes=age_minutes)
    db_session.flush()
    return task


def _page_chips(db_session: Session, catalogue: CatalogueService, count: int) -> None:
    """Add exactly ``count`` page-completeness signals (category, edge, snapshot, screenshot order)."""
    owner = DiscoveryDocumentCandidate(
        jurisdiction_id=catalogue.jurisdiction_id, key=f"k-{uuid.uuid4().hex[:8]}", title_i18n={"de": "x"}
    )
    other = DiscoveryDocumentCandidate(
        jurisdiction_id=catalogue.jurisdiction_id, key=f"k-{uuid.uuid4().hex[:8]}", title_i18n={"de": "y"}
    )
    db_session.add_all([owner, other])
    db_session.flush()
    if count >= 1:
        db_session.add(
            DiscoveryCandidateMention(
                candidate_id=owner.id,
                catalogue_service_id=catalogue.id,
                role=DiscoveryMentionRole.REQUIRED,
                excerpt="x",
                source_field="categories[0]",
                extractor="llm",
                extractor_version="1",
                category_codes=["home-and-housing"],
            )
        )
    if count >= 2:
        db_session.add(
            DiscoveryCandidateEdge(
                parent_candidate_id=owner.id,
                required_candidate_id=other.id,
                catalogue_service_id=catalogue.id,
                excerpt="x",
                basis=DiscoveryEdgeBasis.EXPLICIT,
                extractor="llm",
                extractor_version="1",
            )
        )
    for index, kind in enumerate((DiscoveryArtifactKind.HTML_SNAPSHOT, DiscoveryArtifactKind.SCREENSHOT), start=3):
        if count < index:
            continue
        sha = uuid.uuid4().hex + uuid.uuid4().hex
        db_session.add(
            DiscoveryArtifact(
                catalogue_service_id=catalogue.id,
                kind=kind,
                storage_key=f"discovery/{catalogue.id}/{kind.value}/{sha}",
                sha256=sha,
                content_type="text/html",
                byte_size=10,
                source_url="https://example.gov/page",
                fetched_at=datetime.now(UTC),
            )
        )
    db_session.flush()


def test_claim_pending_without_kinds_ignores_new_task_kinds(queue: TaskQueue, db_session: Session) -> None:
    catalogue = _catalogue(db_session)
    legacy = _seed_task(db_session, catalogue, DiscoveryTaskKind.FETCH_URL, path="fetch")
    new = _seed_task(db_session, catalogue, DiscoveryTaskKind.EXTRACT_PAGE, path="extract")

    claimed = queue.claim_pending(api_key=_key(db_session), limit=10, now=datetime.now(UTC))

    assert [t.id for t in claimed] == [legacy.id]
    assert new.status == DiscoveryTaskStatus.PENDING


def test_claim_pending_with_kinds_returns_only_those_kinds_in_queue_order(
    queue: TaskQueue, db_session: Session
) -> None:
    catalogue = _catalogue(db_session)
    late = _seed_task(db_session, catalogue, DiscoveryTaskKind.EXTRACT_PAGE, path="late", age_minutes=1)
    early = _seed_task(db_session, catalogue, DiscoveryTaskKind.EXTRACT_PAGE, path="early", age_minutes=9)
    urgent = _seed_task(db_session, catalogue, DiscoveryTaskKind.CAPTURE_SCREENSHOT, path="urgent", priority=10)
    _seed_task(db_session, catalogue, DiscoveryTaskKind.FETCH_URL, path="legacy", priority=1)

    kinds = (DiscoveryTaskKind.EXTRACT_PAGE, DiscoveryTaskKind.CAPTURE_SCREENSHOT)
    claimed = queue.claim_pending(api_key=_key(db_session), limit=10, now=datetime.now(UTC), kinds=kinds)

    assert [t.id for t in claimed] == [urgent.id, early.id, late.id]


def test_list_pending_tasks_for_claim_prefers_higher_completeness_within_the_same_priority(
    queue: TaskQueue, db_session: Session
) -> None:
    bare = _catalogue(db_session, external_id=f"bare-{uuid.uuid4().hex[:8]}")
    busy = _catalogue(db_session, external_id=f"busy-{uuid.uuid4().hex[:8]}")
    _page_chips(db_session, busy, 4)
    older = _seed_task(db_session, bare, DiscoveryTaskKind.EXTRACT_PAGE, path="older", age_minutes=9)
    newer = _seed_task(db_session, busy, DiscoveryTaskKind.EXTRACT_PAGE, path="newer", age_minutes=1)

    claimed = queue.claim_pending(
        api_key=_key(db_session), limit=10, now=datetime.now(UTC), kinds=(DiscoveryTaskKind.EXTRACT_PAGE,)
    )

    assert [t.id for t in claimed] == [newer.id, older.id]


def test_list_pending_tasks_for_claim_still_respects_priority_over_completeness(
    queue: TaskQueue, db_session: Session
) -> None:
    bare = _catalogue(db_session, external_id=f"urgent-bare-{uuid.uuid4().hex[:8]}")
    done = _catalogue(db_session, external_id=f"relaxed-done-{uuid.uuid4().hex[:8]}")
    _page_chips(db_session, done, 4)
    urgent = _seed_task(db_session, bare, DiscoveryTaskKind.EXTRACT_PAGE, path="urgent", priority=10)
    relaxed = _seed_task(db_session, done, DiscoveryTaskKind.EXTRACT_PAGE, path="relaxed", priority=100)

    claimed = queue.claim_pending(
        api_key=_key(db_session), limit=10, now=datetime.now(UTC), kinds=(DiscoveryTaskKind.EXTRACT_PAGE,)
    )

    assert [t.id for t in claimed] == [urgent.id, relaxed.id]


NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)


def _leased(queue: TaskQueue, db_session: Session, *, attempts: int) -> DiscoveryTask:
    """Seed a fetch task and lease it ``attempts`` times, as a worker would."""
    task = _seed_task(db_session, _catalogue(db_session), DiscoveryTaskKind.FETCH_URL, path="retry")
    key = _key(db_session)
    for _ in range(attempts):
        task.status = DiscoveryTaskStatus.PENDING
        db_session.flush()
        queue.claim_pending(api_key=key, limit=1, now=NOW)
    return task


def test_claim_pending_counts_one_attempt_per_lease(queue: TaskQueue, db_session: Session) -> None:
    task = _seed_task(db_session, _catalogue(db_session), DiscoveryTaskKind.FETCH_URL, path="count")

    queue.claim_pending(api_key=_key(db_session), limit=1, now=NOW)

    assert task.attempt_count == 1


def test_retryable_failure_returns_the_task_to_pending_with_a_backoff(queue: TaskQueue, db_session: Session) -> None:
    task = _leased(queue, db_session, attempts=1)

    queue.fail(task.id, "connection reset", retryable=True, now=NOW)

    assert task.status == DiscoveryTaskStatus.PENDING
    assert task.not_before == NOW + BACKOFF[0]
    assert task.attempt_count == 1
    assert task.last_error == "connection reset"
    assert task.lease_expires_at is None
    assert task.claimed_by_api_key_id is None


def test_retryable_failure_backs_off_longer_on_each_attempt(queue: TaskQueue, db_session: Session) -> None:
    task = _leased(queue, db_session, attempts=2)

    queue.fail(task.id, "timeout", retryable=True, now=NOW)

    assert task.not_before == NOW + BACKOFF[1]


def test_permanent_failure_stays_failed(queue: TaskQueue, db_session: Session) -> None:
    task = _leased(queue, db_session, attempts=1)

    queue.fail(task.id, "http 404", retryable=False, now=NOW)

    assert task.status == DiscoveryTaskStatus.FAILED
    assert task.not_before is None
    assert task.last_error == "http 404"
    assert task.lease_expires_at is None


def test_retryable_failure_at_the_attempt_cap_becomes_failed(queue: TaskQueue, db_session: Session) -> None:
    task = _leased(queue, db_session, attempts=MAX_ATTEMPTS)

    queue.fail(task.id, "timeout", retryable=True, now=NOW)

    assert task.status == DiscoveryTaskStatus.FAILED
    assert task.not_before is None
    assert task.last_error == "timeout"


def test_claim_skips_a_pending_task_whose_not_before_is_in_the_future(queue: TaskQueue, db_session: Session) -> None:
    task = _seed_task(db_session, _catalogue(db_session), DiscoveryTaskKind.FETCH_URL, path="held")
    task.not_before = NOW + timedelta(minutes=5)

    claimed = queue.claim_pending(api_key=_key(db_session), limit=5, now=NOW)

    assert claimed == []
    assert task.status == DiscoveryTaskStatus.PENDING
    assert task.attempt_count == 0


def test_claim_takes_a_pending_task_once_not_before_has_passed(queue: TaskQueue, db_session: Session) -> None:
    held = _seed_task(db_session, _catalogue(db_session), DiscoveryTaskKind.FETCH_URL, path="held")
    held.not_before = NOW + timedelta(minutes=5)
    db_session.flush()

    claimed = queue.claim_pending(api_key=_key(db_session), limit=5, now=NOW + timedelta(minutes=5))

    assert [t.id for t in claimed] == [held.id]


def _expire_lease(task: DiscoveryTask, db_session: Session) -> None:
    task.lease_expires_at = NOW - timedelta(minutes=1)
    db_session.flush()


def test_reclaim_of_an_expired_lease_below_the_cap_returns_the_task_to_pending(
    queue: TaskQueue, db_session: Session
) -> None:
    task = _leased(queue, db_session, attempts=MAX_ATTEMPTS - 1)
    _expire_lease(task, db_session)

    queue.claim_pending(api_key=_key(db_session), limit=0, now=NOW)
    db_session.refresh(task)

    assert task.status == DiscoveryTaskStatus.PENDING
    assert task.attempt_count == MAX_ATTEMPTS - 1


def test_reclaim_of_an_expired_lease_at_the_cap_marks_the_task_failed(queue: TaskQueue, db_session: Session) -> None:
    task = _leased(queue, db_session, attempts=MAX_ATTEMPTS)
    _expire_lease(task, db_session)

    claimed = queue.claim_pending(api_key=_key(db_session), limit=5, now=NOW)
    db_session.refresh(task)

    assert claimed == []
    assert task.status == DiscoveryTaskStatus.FAILED
    assert task.last_error == f"lease expired after {MAX_ATTEMPTS} attempts"
    assert task.lease_expires_at is None


def test_render_page_is_claimed_only_with_an_explicit_kinds_filter(queue: TaskQueue, db_session: Session) -> None:
    catalogue = _catalogue(db_session)
    render = _seed_task(db_session, catalogue, DiscoveryTaskKind.RENDER_PAGE, path="render")
    key = _key(db_session)

    by_default = queue.claim_pending(api_key=key, limit=5, now=NOW)
    explicit = queue.claim_pending(api_key=key, limit=5, now=NOW, kinds=(DiscoveryTaskKind.RENDER_PAGE,))

    assert by_default == []
    assert [t.id for t in explicit] == [render.id]


def test_llm_extract_is_never_claimed_by_default_but_is_with_an_explicit_kinds_filter(
    queue: TaskQueue, db_session: Session
) -> None:
    catalogue = _catalogue(db_session)
    extract = _seed_task(db_session, catalogue, DiscoveryTaskKind.LLM_EXTRACT, path="llm")
    key = _key(db_session)

    by_default = queue.claim_pending(api_key=key, limit=5, now=NOW)
    explicit = queue.claim_pending(api_key=key, limit=5, now=NOW, kinds=(DiscoveryTaskKind.LLM_EXTRACT,))

    assert by_default == []
    assert [t.id for t in explicit] == [extract.id]


def test_release_returns_a_claimed_task_to_pending_without_consuming_an_attempt(
    queue: TaskQueue, db_session: Session
) -> None:
    task = _leased(queue, db_session, attempts=1)
    assert (task.attempt_count, task.status) == (1, DiscoveryTaskStatus.CLAIMED)

    released = queue.release(task.id, "browser_quota")

    assert released.status == DiscoveryTaskStatus.PENDING
    assert (released.lease_expires_at, released.claimed_at, released.claimed_by_api_key_id) == (None, None, None)
    assert (released.attempt_count, released.last_error) == (0, "browser_quota")
    reclaimed = queue.claim_pending(api_key=_key(db_session), limit=1, now=NOW)
    assert [t.id for t in reclaimed] == [task.id]
    assert task.attempt_count == 1


def test_release_never_takes_attempt_count_below_zero_and_records_an_event(
    queue: TaskQueue, db_session: Session
) -> None:
    task = _leased(queue, db_session, attempts=1)
    task.attempt_count = 0

    queue.release(task.id, "storage_unavailable")

    assert task.attempt_count == 0
    events = db_session.scalars(select(DiscoveryEvent).where(DiscoveryEvent.discovery_task_id == task.id)).all()
    released = [e for e in events if e.event_type == DiscoveryEventType.TASK_RELEASED]
    assert [e.payload for e in released] == [{"reason": "storage_unavailable"}]


def test_release_rejects_a_task_that_is_not_claimed_and_an_unknown_task(queue: TaskQueue, db_session: Session) -> None:
    pending = _seed_task(db_session, _catalogue(db_session), DiscoveryTaskKind.FETCH_URL, path="pending")

    with pytest.raises(TaskNotClaimedError):
        queue.release(pending.id, "nope")
    with pytest.raises(DiscoveryTaskNotFoundError):
        queue.release(uuid.uuid4(), "nope")
    assert pending.last_error is None


def test_a_released_task_is_claimable_again_once_not_before_has_passed_and_not_before(
    queue: TaskQueue, db_session: Session
) -> None:
    task = _leased(queue, db_session, attempts=1)
    later = NOW + timedelta(minutes=30)
    queue.release(task.id, "browser_quota", not_before=later)
    key = _key(db_session)

    too_early = queue.claim_pending(api_key=key, limit=1, now=NOW + timedelta(minutes=29))
    in_time = queue.claim_pending(api_key=key, limit=1, now=later)

    assert too_early == []
    assert [t.id for t in in_time] == [task.id]


def test_complete_stores_an_optional_note_and_clears_the_lease(queue: TaskQueue, db_session: Session) -> None:
    task = _leased(queue, db_session, attempts=1)

    queue.complete(task.id, note="no_mentions")

    assert (task.status, task.result_note, task.lease_expires_at) == (
        DiscoveryTaskStatus.COMPLETED,
        "no_mentions",
        None,
    )
