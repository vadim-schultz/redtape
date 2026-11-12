"""HTTP behavior of the translation admin coverage route (chapter 06)."""

from __future__ import annotations

from uuid import uuid4

from app.models.search import WorkTaskStatus
from app.models.translation import CandidateTranslation, TranslationTask
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from search_support import make_candidate
from test_discovery_admin_api import _admin_headers, _token
from test_discovery_admin_api import client as client  # noqa: F401
from test_discovery_machine_api import _issue_key
from translation_support import (
    claimed_by,
    configured_locales,
    enqueuer,
    make_key,
    stored_row,
    task_rows,
    unit_candidate,
    unit_hash,
)

COVERAGE = "/api/v1/admin/translations/coverage"
ZERO = {"translated": 0, "stale": 0, "pending": 0, "claimed": 0, "failed": 0}


def _by_locale(body: dict[str, list[dict[str, object]]]) -> dict[str, dict[str, object]]:
    return {str(row["locale"]): row for row in body["locales"]}


def _written_counts(session: Session) -> tuple[int, int]:
    tasks = session.scalar(select(func.count()).select_from(TranslationTask))
    rows = session.scalar(select(func.count()).select_from(CandidateTranslation))
    return int(tasks or 0), int(rows or 0)


def test_coverage_counts_translated_stale_pending_claimed_and_failed_per_configured_locale(
    client: TestClient[Litestar], db_session: Session
) -> None:
    done = unit_candidate(db_session, "Gut")
    replaced = unit_candidate(db_session, "Alt")
    waiting = unit_candidate(db_session, "Neu")
    running = unit_candidate(db_session, "Laufend")
    broken = unit_candidate(db_session, "Kaputt")
    stored_row(db_session, done, "en", unit_hash(db_session, done))
    stored_row(db_session, replaced, "en", "old-hash")
    enqueuer(db_session, ("en",)).enqueue_many([replaced.id, waiting.id, running.id, broken.id])
    tasks = {task.candidate_id: task for task in task_rows(db_session)}
    claimed_by(db_session, tasks[running.id], make_key(db_session))
    tasks[broken.id].status = WorkTaskStatus.FAILED
    db_session.flush()

    response = client.get(COVERAGE, headers=_admin_headers())

    assert response.status_code == 200
    en = _by_locale(response.json())["en"]
    assert (en["translated"], en["stale"], en["pending"], en["claimed"], en["failed"]) == (2, 1, 2, 1, 1)
    assert [row["locale"] for row in response.json()["locales"]] == list(configured_locales())


def test_a_locale_with_no_rows_still_appears_with_zeros(client: TestClient[Litestar], db_session: Session) -> None:
    unit_candidate(db_session, "Gut")

    body = client.get(COVERAGE, headers=_admin_headers()).json()

    assert _by_locale(body)["ru"] == {"locale": "ru", **ZERO}


def test_the_denominator_counts_candidates_with_a_german_card_source(
    client: TestClient[Litestar], db_session: Session
) -> None:
    make_candidate(db_session, "Kindergeldantrag")
    make_candidate(db_session, "Wohngeld")
    make_candidate(db_session, "")
    make_candidate(db_session, "   ")
    english_only = make_candidate(db_session, "")
    english_only.title_i18n = {"en": "Child benefit"}
    db_session.flush()

    body = client.get(COVERAGE, headers=_admin_headers()).json()

    assert body["denominator"] == 2


def test_a_caller_outside_the_admin_allowlist_is_refused(client: TestClient[Litestar], db_session: Session) -> None:
    stranger = {"Authorization": f"Bearer {_token(sub=uuid4(), email='stranger@example.com')}"}
    machine = {"X-API-Key": _issue_key(db_session)}

    assert client.get(COVERAGE, headers=stranger).status_code == 403
    assert client.get(COVERAGE).status_code == 401
    assert client.get(COVERAGE, headers=machine).status_code == 401


def test_the_endpoint_writes_nothing_and_enqueues_nothing(client: TestClient[Litestar], db_session: Session) -> None:
    done = unit_candidate(db_session, "Gut")
    unit_candidate(db_session, "Neu")
    stored_row(db_session, done, "en", unit_hash(db_session, done))
    db_session.flush()
    before = _written_counts(db_session)

    response = client.get(COVERAGE, headers=_admin_headers())

    assert response.status_code == 200
    assert _written_counts(db_session) == before == (0, 1)
    assert not db_session.new and not db_session.dirty and not db_session.deleted
