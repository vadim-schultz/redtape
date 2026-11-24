"""Queue summary counts and the machine summary route (chapter 5)."""

from __future__ import annotations

from datetime import timedelta

from app.features.discovery.repository import DiscoveryRepository
from app.models.discovery import LEGACY_TASK_KINDS, DiscoveryTask, DiscoveryTaskKind, DiscoveryTaskStatus
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy.orm import Session

from test_discovery_admin_api import _catalogue
from test_discovery_machine_api import SUMMARY_URL, _issue_key, _seed_pending, client  # noqa: F401
from test_discovery_task_queue import NOW, _seed_task


def _task_in_state(
    db_session: Session,
    status: DiscoveryTaskStatus,
    *,
    path: str,
    kind: DiscoveryTaskKind = DiscoveryTaskKind.FETCH_URL,
) -> DiscoveryTask:
    task = _seed_task(db_session, _catalogue(db_session, external_id=path), kind, path=path)
    task.status = status
    db_session.flush()
    return task


def _seed_mixed_queue(db_session: Session) -> DiscoveryTask:
    _task_in_state(db_session, DiscoveryTaskStatus.PENDING, path="ready")
    delayed = _task_in_state(db_session, DiscoveryTaskStatus.PENDING, path="delayed")
    delayed.not_before = NOW + timedelta(minutes=5)
    live = _task_in_state(db_session, DiscoveryTaskStatus.CLAIMED, path="live")
    live.lease_expires_at = NOW + timedelta(minutes=5)
    stale = _task_in_state(db_session, DiscoveryTaskStatus.CLAIMED, path="stale")
    stale.lease_expires_at = NOW - timedelta(minutes=5)
    _task_in_state(db_session, DiscoveryTaskStatus.COMPLETED, path="done")
    _task_in_state(db_session, DiscoveryTaskStatus.FAILED, path="broken")
    db_session.flush()
    return stale


def test_summary_counts_ready_and_delayed_pending_tasks_separately(db_session: Session) -> None:
    _seed_mixed_queue(db_session)

    summary = DiscoveryRepository(db_session).task_summary(kinds=LEGACY_TASK_KINDS, now=NOW)

    assert (summary.pending_ready, summary.pending_delayed) == (1, 1)
    assert (summary.claimed, summary.claimed_stale) == (2, 1)
    assert (summary.completed, summary.failed) == (1, 1)


def test_summary_never_leases_or_mutates_tasks(db_session: Session) -> None:
    stale = _seed_mixed_queue(db_session)

    DiscoveryRepository(db_session).task_summary(kinds=LEGACY_TASK_KINDS, now=NOW)

    assert stale.status == DiscoveryTaskStatus.CLAIMED
    assert stale.attempt_count == 0


def test_summary_counts_only_the_requested_kinds(db_session: Session) -> None:
    _task_in_state(db_session, DiscoveryTaskStatus.PENDING, path="fetch")
    _task_in_state(db_session, DiscoveryTaskStatus.PENDING, path="extract", kind=DiscoveryTaskKind.EXTRACT_PAGE)
    repository = DiscoveryRepository(db_session)

    legacy = repository.task_summary(kinds=LEGACY_TASK_KINDS, now=NOW)
    extract = repository.task_summary(kinds=(DiscoveryTaskKind.EXTRACT_PAGE,), now=NOW)

    assert legacy.pending_ready == 1
    assert extract.pending_ready == 1


def test_summary_of_an_empty_queue_is_all_zero(db_session: Session) -> None:
    summary = DiscoveryRepository(db_session).task_summary(kinds=LEGACY_TASK_KINDS, now=NOW)

    assert summary.pending_ready == summary.pending_delayed == summary.claimed == summary.claimed_stale == 0
    assert summary.completed == summary.failed == 0


def test_get_summary_route_defaults_to_the_legacy_kinds(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    key = _issue_key(db_session)
    _seed_pending(db_session, DiscoveryTaskKind.FETCH_URL)
    _seed_pending(db_session, DiscoveryTaskKind.EXTRACT_PAGE)

    response = client.get(SUMMARY_URL, headers={"X-API-Key": key})

    assert response.status_code == 200
    assert response.json()["pending_ready"] == 1


def test_get_summary_route_honours_the_kinds_query(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    key = _issue_key(db_session)
    _seed_pending(db_session, DiscoveryTaskKind.FETCH_URL)
    _seed_pending(db_session, DiscoveryTaskKind.EXTRACT_PAGE)

    response = client.get(SUMMARY_URL, params={"kinds": ["extract_page"]}, headers={"X-API-Key": key})

    assert response.status_code == 200
    assert response.json()["pending_ready"] == 1
    assert set(response.json()) == {
        "pending_ready",
        "pending_delayed",
        "claimed",
        "claimed_stale",
        "completed",
        "failed",
        "oldest_pending_age_seconds",
        "completed_24h",
        "failed_24h",
    }


def test_get_summary_route_requires_the_machine_api_key(client: TestClient[Litestar]) -> None:  # noqa: F811
    response = client.get(SUMMARY_URL)

    assert response.status_code == 401


def test_get_summary_route_rejects_unknown_kinds(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    key = _issue_key(db_session)

    response = client.get(SUMMARY_URL, params={"kinds": ["no_such_kind"]}, headers={"X-API-Key": key})

    assert response.status_code == 422


def test_the_summary_reports_oldest_pending_age_and_the_24_hour_counts(db_session: Session) -> None:
    """stats · the age is the oldest ready row (a delayed older row does not count); a row finished 25 h ago is not in the 24 h counts."""
    old_ready = _task_in_state(db_session, DiscoveryTaskStatus.PENDING, path="old-ready")
    old_ready.created_at = NOW - timedelta(hours=2)
    new_ready = _task_in_state(db_session, DiscoveryTaskStatus.PENDING, path="new-ready")
    new_ready.created_at = NOW - timedelta(minutes=5)
    delayed = _task_in_state(db_session, DiscoveryTaskStatus.PENDING, path="old-delayed")
    delayed.created_at = NOW - timedelta(hours=9)
    delayed.not_before = NOW + timedelta(minutes=5)
    recent_done = _task_in_state(db_session, DiscoveryTaskStatus.COMPLETED, path="recent-done")
    recent_done.updated_at = NOW - timedelta(hours=1)
    old_done = _task_in_state(db_session, DiscoveryTaskStatus.COMPLETED, path="old-done")
    old_done.updated_at = NOW - timedelta(hours=25)
    recent_failed = _task_in_state(db_session, DiscoveryTaskStatus.FAILED, path="recent-failed")
    recent_failed.updated_at = NOW - timedelta(hours=3)
    old_failed = _task_in_state(db_session, DiscoveryTaskStatus.FAILED, path="old-failed")
    old_failed.updated_at = NOW - timedelta(hours=25)
    db_session.flush()

    summary = DiscoveryRepository(db_session).task_summary(kinds=LEGACY_TASK_KINDS, now=NOW)

    assert summary.oldest_pending_age_seconds == 2 * 3600
    assert (summary.completed_24h, summary.failed_24h) == (1, 1)
    assert (summary.pending_ready, summary.pending_delayed) == (2, 1)


def test_the_oldest_pending_age_of_a_queue_with_nothing_ready_is_none(db_session: Session) -> None:
    """stats · with no ready task there is no oldest pending age to report, and the 24 h counts are zero."""
    _task_in_state(db_session, DiscoveryTaskStatus.CLAIMED, path="held")

    summary = DiscoveryRepository(db_session).task_summary(kinds=LEGACY_TASK_KINDS, now=NOW)

    assert summary.oldest_pending_age_seconds is None
    assert (summary.completed_24h, summary.failed_24h) == (0, 0)
