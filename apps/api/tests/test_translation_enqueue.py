"""Which translation tasks a candidate's card unit queues, at which priority (chapter 14)."""

from __future__ import annotations

from app.config import settings
from app.features.translation.enqueue import TranslationEnqueuer
from app.features.translation.priority import RETRANSLATION_BASE
from app.features.translation.queue import TranslationQueue
from app.features.translation.source import SourceRepository
from app.features.translation.unit import TranslationUnit
from app.models.search import WorkTaskStatus
from app.models.translation import CandidateTranslation
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from search_support import make_candidate, make_mention
from test_discovery_admin_api import _catalogue
from test_discovery_candidates_api import MENTIONS_URL, _item
from test_discovery_machine_api import _issue_key
from test_discovery_machine_api import client as client  # noqa: F401
from translation_support import (
    LOCALES,
    NOW,
    claimed_by,
    enqueuer,
    human_row,
    make_key,
    stored_row,
    task_rows,
    unit_candidate,
    unit_hash,
)


def _pairs(session: Session) -> set[tuple[object, str]]:
    return {(task.candidate_id, task.locale) for task in task_rows(session)}


def test_a_new_candidate_gets_one_pending_task_per_target_locale_and_rerunning_changes_nothing(
    db_session: Session,
) -> None:
    candidate = unit_candidate(db_session)

    first = enqueuer(db_session).enqueue_many([candidate.id])
    snapshot = [(task.id, task.priority, task.source_hash, task.updated_at) for task in task_rows(db_session)]
    second = enqueuer(db_session).enqueue_many([candidate.id])

    assert _pairs(db_session) == {(candidate.id, locale) for locale in LOCALES}
    assert {task.source_hash for task in task_rows(db_session)} == {unit_hash(db_session, candidate)}
    assert (first.enqueued, second.enqueued) == (2, 0)
    assert snapshot == [(task.id, task.priority, task.source_hash, task.updated_at) for task in task_rows(db_session)]


def test_a_candidate_without_a_german_title_queues_nothing(db_session: Session) -> None:
    untitled = make_candidate(db_session, title="")
    make_mention(db_session, untitled, "Bitte Ausweis mitbringen")

    totals = enqueuer(db_session).enqueue_many([untitled.id])

    assert task_rows(db_session) == []
    assert (totals.enqueued, totals.no_source) == (0, len(LOCALES))


def test_the_unit_is_the_german_title_and_the_best_mention_excerpt_cut_to_the_card_length(db_session: Session) -> None:
    candidate = unit_candidate(db_session, "Antrag", excerpt="x" * 400)

    unit = SourceRepository(db_session).units_for([candidate.id])[candidate.id]

    assert unit == TranslationUnit("Antrag", "x" * 300)
    assert unit.source_hash == unit_hash(db_session, candidate)


def test_a_candidate_whose_translation_is_current_is_left_alone_and_a_stale_pending_task_is_retired(
    db_session: Session,
) -> None:
    candidate = unit_candidate(db_session)
    enqueuer(db_session, ("en",)).enqueue_many([candidate.id])
    stored_row(db_session, candidate, "en", unit_hash(db_session, candidate))

    totals = enqueuer(db_session, ("en", "tr")).enqueue_many([candidate.id])

    assert [(task.locale, task.status) for task in task_rows(db_session)] == [("tr", WorkTaskStatus.PENDING)]
    assert (totals.up_to_date, totals.enqueued) == (1, 1)


def test_a_changed_source_hash_queues_a_retranslation_at_lower_priority_than_a_first_translation(
    db_session: Session,
) -> None:
    fresh, changed = unit_candidate(db_session, "Neu", score=0.1), unit_candidate(db_session, "Alt", score=0.9)
    stored_row(db_session, changed, "en", "old-hash")

    totals = enqueuer(db_session, ("en",)).enqueue_many([fresh.id, changed.id])

    by_candidate = {task.candidate_id: task for task in task_rows(db_session)}
    assert by_candidate[fresh.id].priority < RETRANSLATION_BASE <= by_candidate[changed.id].priority
    assert (totals.enqueued, totals.stale, totals.missing) == (2, 1, 1)


def test_a_pending_task_takes_the_new_hash_and_a_claimed_task_is_left_alone(db_session: Session) -> None:
    pending, claimed = unit_candidate(db_session, "Offen"), unit_candidate(db_session, "Geleast")
    enqueuer(db_session, ("en",)).enqueue_many([pending.id, claimed.id])
    pending_task, claimed_task = (
        next(task for task in task_rows(db_session) if task.candidate_id == owner.id) for owner in (pending, claimed)
    )
    claimed_by(db_session, claimed_task, make_key(db_session))
    for owner, new_title in ((pending, "Offen neu"), (claimed, "Geleast neu")):
        owner.title_i18n = {"de": new_title}
    db_session.flush()

    totals = enqueuer(db_session, ("en",)).enqueue_many([pending.id, claimed.id])

    db_session.refresh(pending_task)
    assert pending_task.source_hash == unit_hash(db_session, pending)
    assert claimed_task.source_hash != unit_hash(db_session, claimed)
    assert (claimed_task.status, len(task_rows(db_session))) == (WorkTaskStatus.CLAIMED, 2)
    assert totals.enqueued == 1


def test_a_human_translation_is_never_queued_for_machine_translation(db_session: Session) -> None:
    candidate = unit_candidate(db_session)
    human_row(db_session, candidate, "en")

    totals = enqueuer(db_session).enqueue_many([candidate.id])

    assert [task.locale for task in task_rows(db_session)] == ["tr"]
    assert totals.human_protected == 1


def test_a_changed_translation_unit_recipe_makes_every_translation_stale(
    db_session: Session, monkeypatch: object
) -> None:
    candidate = unit_candidate(db_session)
    stored_row(db_session, candidate, "en", unit_hash(db_session, candidate))
    monkeypatch.setattr(settings, "translation_unit_recipe_version", "v2")  # type: ignore[attr-defined]

    totals = enqueuer(db_session, ("en",)).enqueue_many([candidate.id])

    assert (totals.stale, totals.up_to_date, totals.enqueued) == (1, 0, 1)


def test_higher_confidence_candidates_are_claimed_first_and_all_locales_of_one_candidate_stay_together(
    db_session: Session,
) -> None:
    low, high, middle = (
        unit_candidate(db_session, title, score=score)
        for title, score in (("Niedrig", 0.2), ("Hoch", 0.9), ("Mittel", 0.5))
    )
    enqueuer(db_session).enqueue_many([low.id, high.id, middle.id])

    claimed = TranslationQueue(db_session, clock=lambda: NOW).claim(make_key(db_session).id, limit=6).items

    assert [item.candidate_id for item in claimed] == [high.id] * 2 + [middle.id] * 2 + [low.id] * 2
    assert sorted(item.locale for item in claimed[:2]) == sorted(LOCALES)


def test_a_candidate_without_any_score_ranks_after_scored_candidates(db_session: Session) -> None:
    unscored, scored = unit_candidate(db_session, "Ohne"), unit_candidate(db_session, "Mit", score=0.3)
    enqueuer(db_session, ("en",)).enqueue_many([unscored.id, scored.id])

    claimed = TranslationQueue(db_session, clock=lambda: NOW).claim(make_key(db_session).id, limit=2).items

    assert [item.candidate_id for item in claimed] == [scored.id, unscored.id]


def test_a_pending_task_follows_the_confidence_of_its_candidate(db_session: Session) -> None:
    candidate = unit_candidate(db_session, score=0.2)
    enqueuer(db_session, ("en",)).enqueue_many([candidate.id])
    (task,) = task_rows(db_session)
    before = task.priority
    make_mention(db_session, candidate, "Zweite Stelle", 0.95).category_codes = ["home-and-housing"]
    db_session.flush()

    enqueuer(db_session, ("en",)).enqueue_many([candidate.id])

    db_session.refresh(task)
    assert task.priority < before


def test_the_default_enqueuer_translates_into_the_configured_target_locales(db_session: Session) -> None:
    candidate = unit_candidate(db_session)

    TranslationEnqueuer(db_session).enqueue_many([candidate.id])

    assert {task.locale for task in task_rows(db_session)} == set(settings.translation_target_locale_codes)
    assert not db_session.scalars(select(CandidateTranslation)).all()


def test_candidates_of_equal_confidence_are_still_finished_one_at_a_time_across_locales(db_session: Session) -> None:
    candidates = [unit_candidate(db_session, f"Gleich {n}", score=0.5) for n in range(8)]
    enqueuer(db_session).enqueue_many([candidate.id for candidate in candidates])

    claimed = TranslationQueue(db_session, clock=lambda: NOW).claim(make_key(db_session).id, limit=16).items

    owners = [item.candidate_id for item in claimed]
    assert len(claimed) == 16
    assert owners[0::2] == owners[1::2]


def test_recording_a_mention_queues_one_translation_task_per_target_locale_and_a_repost_queues_nothing(
    client: TestClient[Litestar],
    db_session: Session,  # noqa: F811
) -> None:
    key, catalogue = _issue_key(db_session), _catalogue(db_session)
    body = {"items": [_item(catalogue)]}

    first = client.post(MENTIONS_URL, json=body, headers={"X-API-Key": key})
    snapshot = [(task.id, task.priority, task.updated_at) for task in task_rows(db_session)]
    second = client.post(MENTIONS_URL, json=body, headers={"X-API-Key": key})

    assert (first.status_code, second.status_code) == (200, 200)
    assert {task.locale for task in task_rows(db_session)} == set(settings.translation_target_locale_codes)
    assert snapshot == [(task.id, task.priority, task.updated_at) for task in task_rows(db_session)]
    assert {task.source_hash for task in task_rows(db_session)} == {
        SourceRepository(db_session)
        .units_for([task_rows(db_session)[0].candidate_id])[task_rows(db_session)[0].candidate_id]
        .source_hash
    }


def test_a_rejected_mention_batch_queues_no_translation_task(
    client: TestClient[Litestar],
    db_session: Session,  # noqa: F811
) -> None:
    key, catalogue = _issue_key(db_session), _catalogue(db_session)
    bad = _item(catalogue, title_i18n={"de": "   "})

    response = client.post(MENTIONS_URL, json={"items": [bad]}, headers={"X-API-Key": key})

    assert response.status_code == 422
    assert task_rows(db_session) == []
