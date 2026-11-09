"""The SQL category-score relation mirrors the Python scorer for the whole candidate pool, with no inclusion floor.

``candidate_category_support`` is the reference: for every category of every candidate the relation's score must
equal it within ``1e-6`` (the noisy-OR clamp keeps ``ln`` finite for a ``1.0`` source).
"""

from __future__ import annotations

import math
import uuid

import pytest
from app.features.discovery.repository.candidate_category_support import candidate_category_support
from app.features.discovery.repository.candidate_tag_scores import tag_scores_subquery
from app.features.discovery.tags import MANUAL_EXTRACTOR, MIN_SUGGESTED_SCORE
from sqlalchemy import select
from sqlalchemy.orm import Session

import completeness_world as world
from completeness_world import Row

TOLERANCE = 1e-6
FLOOR_POOL = 25


def _sql_scores(session: Session, candidate_id: uuid.UUID) -> dict[str, float]:
    """Return the relation's score of every category of ``candidate_id``."""
    rel = tag_scores_subquery()
    stmt = select(rel.c.code, rel.c.score).where(rel.c.candidate_id == candidate_id)
    return {row.code: row.score for row in session.execute(stmt)}


def _python_scores(session: Session, candidate_id: uuid.UUID) -> dict[str, float]:
    return {s.code: s.score for s in candidate_category_support(session, candidate_id)}


def _staged(session: Session, rows: list[Row], procs: int = 2) -> uuid.UUID:
    procedures = world.procedures(session, procs)
    subject = world.candidate(session, procedures[0], f"subject-{uuid.uuid4().hex[:6]}")
    world.mentioned(session, subject, procedures, rows)
    return subject.id


def _assert_parity(session: Session, candidate_id: uuid.UUID) -> None:
    expected = _python_scores(session, candidate_id)
    actual = _sql_scores(session, candidate_id)
    assert actual.keys() == expected.keys()
    assert actual == pytest.approx(expected, abs=TOLERANCE)


PARITY_CASES: dict[str, tuple[list[Row], int]] = {
    "llm-one-procedure": ([Row(0, ["housing", "moving-house"])], 1),
    "llm-two-procedures": ([Row(0, ["housing", "moving-house"]), Row(1, ["housing", "moving-house"])], 2),
    "llm-partial-share": ([Row(0, ["housing", "work"]), Row(1, ["housing"]), Row(1, ["moving-house"])], 3),
    "pvog-alone": ([Row(0, ["housing"], "pvog", 0.6, "1050200")], 1),
    "llm-plus-pvog": ([Row(0, ["housing"]), Row(1, ["housing"], "pvog", 0.6)], 2),
    "two-direct-sources": ([Row(0, ["housing"], "pvog", 0.6), Row(1, ["housing"], "pvog", 0.5)], 2),
    "manual-override": ([Row(0, ["housing"]), Row(1, ["housing"]), Row(0, ["work"], MANUAL_EXTRACTOR)], 2),
    "manual-without-codes": ([Row(0, ["housing"]), Row(0, None, MANUAL_EXTRACTOR)], 1),
    "mentions-without-codes": ([Row(0, ["housing"]), Row(1, None), Row(2, [])], 3),
}


@pytest.mark.parametrize("case", PARITY_CASES)
def test_sql_score_equals_the_python_scorer(db_session: Session, case: str) -> None:
    rows, procs = PARITY_CASES[case]

    _assert_parity(db_session, _staged(db_session, rows, procs))


def test_a_code_below_the_old_floor_is_present_with_its_exact_score(db_session: Session) -> None:
    rows = [Row(0, ["rare"]), *(Row(index, ["common"]) for index in range(FLOOR_POOL))]
    candidate_id = _staged(db_session, rows, procs=FLOOR_POOL)

    scores = _sql_scores(db_session, candidate_id)

    assert 0 < scores["rare"] < MIN_SUGGESTED_SCORE
    _assert_parity(db_session, candidate_id)


def test_a_candidate_without_mentions_has_no_rows(db_session: Session) -> None:
    procedure = world.procedures(db_session, 1)[0]
    bare = world.candidate(db_session, procedure, "bare")

    assert _sql_scores(db_session, bare.id) == {}


def test_a_manual_override_hides_the_consensus(db_session: Session) -> None:
    rows = [
        Row(0, ["housing", "moving-house"]),
        Row(1, ["housing", "moving-house"]),
        Row(0, ["work"], MANUAL_EXTRACTOR),
    ]
    candidate_id = _staged(db_session, rows)

    assert _sql_scores(db_session, candidate_id) == {"work": 1.0}


def test_a_direct_confidence_of_one_scores_one_not_nan(db_session: Session) -> None:
    candidate_id = _staged(db_session, [Row(0, ["housing"], "pvog", 1.0)], procs=1)

    score = _sql_scores(db_session, candidate_id)["housing"]

    assert not math.isnan(score)
    assert score == pytest.approx(1.0, abs=TOLERANCE)
    _assert_parity(db_session, candidate_id)
