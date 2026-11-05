"""One category scoring engine in SQL, shared by the bulk completeness path and the single-candidate detail path.

The continuous score combines the LLM-evidence curve via noisy-OR with any direct-source confidence. These tests
pin the manual override, the inclusion floor, and the agreement between the bulk and single-candidate paths.
"""

from __future__ import annotations

import uuid

import pytest
from app.features.candidates.repository.tag_scores import TagScoreRepository
from app.features.discovery.candidate_tags import candidate_category_suggestions, usable_codes
from app.features.discovery.repository.candidate_category_support import candidate_category_support
from app.features.discovery.repository.candidate_leaf_codes import candidate_category_leaf_codes
from app.features.discovery.tags import MANUAL_EXTRACTOR, MIN_SUGGESTED_SCORE, TagSupport
from sqlalchemy.orm import Session

import completeness_world as world
from completeness_world import Row


def _staged(session: Session, rows: list[Row], procs: int = 2, key: str = "subject") -> uuid.UUID:
    procedures = world.procedures(session, procs)
    subject = world.candidate(session, procedures[0], key)
    world.mentioned(session, subject, procedures, rows)
    return subject.id


def _support(session: Session, subject_id: uuid.UUID) -> dict[str, TagSupport]:
    return {support.code: support for support in candidate_category_support(session, subject_id)}


def test_category_support_counts_distinct_procedures_not_mentions(db_session: Session) -> None:
    rows = [Row(0, ["housing"]), Row(0, ["housing"]), Row(0, ["housing", "work"]), Row(1, ["housing"])]
    result = _support(db_session, _staged(db_session, rows))

    assert (result["housing"].procedures, result["housing"].share) == (2, 1.0)
    assert (result["work"].procedures, result["work"].share) == (1, 0.5)
    assert result["housing"].score > result["work"].score


def test_category_support_ignores_mentions_without_codes_in_the_share(db_session: Session) -> None:
    rows = [Row(0, ["a"]), Row(1, ["a"]), Row(2, None), Row(3, [])]
    subject_id = _staged(db_session, rows, procs=4)

    assert candidate_category_support(db_session, subject_id) == [
        TagSupport("a", procedures=2, share=1.0, score=pytest.approx(0.85))
    ]
    other_id = _staged(db_session, [Row(0, None), Row(1, [])], procs=2, key="other")
    assert candidate_category_support(db_session, other_id) == []


def test_category_support_orders_most_supported_code_first(db_session: Session) -> None:
    rows = [Row(0, ["b", "a"]), Row(1, ["a"])]
    result = candidate_category_support(db_session, _staged(db_session, rows, procs=2))

    assert [support.code for support in result] == ["a", "b"]
    assert result[0].procedures >= result[1].procedures


def test_a_manual_mention_takes_one_procedure_and_replaces_the_consensus(db_session: Session) -> None:
    rows = [Row(0, ["housing"]), Row(1, ["housing"]), Row(0, ["work"], MANUAL_EXTRACTOR)]
    result = candidate_category_support(db_session, _staged(db_session, rows, procs=2))

    assert result == [TagSupport("work", procedures=1, share=1.0, score=1.0)]


def test_manual_mentions_union_over_procedures(db_session: Session) -> None:
    rows = [Row(0, ["b", "a"], MANUAL_EXTRACTOR), Row(1, ["a"], MANUAL_EXTRACTOR)]
    result = candidate_category_support(db_session, _staged(db_session, rows, procs=2))

    assert result == [
        TagSupport("a", procedures=2, share=1.0, score=1.0),
        TagSupport("b", procedures=1, share=1.0, score=1.0),
    ]


def test_a_manual_mention_without_codes_does_not_replace_the_consensus(db_session: Session) -> None:
    rows = [Row(0, ["housing"], "llm"), Row(0, None, MANUAL_EXTRACTOR), Row(0, [], MANUAL_EXTRACTOR)]
    result = candidate_category_support(db_session, _staged(db_session, rows, procs=1))

    assert result == [TagSupport("housing", procedures=1, share=1.0, score=pytest.approx(0.5))]


def test_a_single_procedure_clears_the_inclusion_floor_for_every_category(db_session: Session) -> None:
    subject_id = _staged(db_session, [Row(0, ["housing", "moving-house"])], procs=1)

    assert usable_codes(candidate_category_suggestions(db_session, subject_id)) == ["housing", "moving-house"]


def test_a_direct_confidence_mention_combines_with_llm_evidence_via_noisy_or(db_session: Session) -> None:
    """A PVOG-shaped direct assertion and an LLM-extracted one on the same code corroborate."""
    llm_only_id = _staged(db_session, [Row(0, ["a"])], procs=1, key="llm")
    direct_only_id = _staged(db_session, [Row(0, ["a"], "pvog", 0.6)], procs=1, key="direct")
    both_id = _staged(db_session, [Row(0, ["a"]), Row(1, ["a"], "pvog", 0.6)], procs=2, key="both")

    llm_only = _support(db_session, llm_only_id)["a"].score
    direct_only = _support(db_session, direct_only_id)["a"].score
    both = _support(db_session, both_id)["a"].score

    assert both > llm_only
    assert both > direct_only


def test_category_score_matches_the_sql_aggregation_and_keeps_the_existing_curve(db_session: Session) -> None:
    subject_id = _staged(db_session, [Row(0, ["moving-house"]), Row(1, ["moving-house"])], procs=2)

    python_score = candidate_category_support(db_session, subject_id)
    sql_score = TagScoreRepository(db_session).tag_scores_for([subject_id])[subject_id]

    assert python_score == [TagSupport("moving-house", 2, 1.0, pytest.approx(0.85))]
    assert [(row.code, row.score) for row in sql_score] == [("moving-house", pytest.approx(0.85))]


def test_a_single_low_share_llm_mention_scores_below_the_inclusion_floor(db_session: Session) -> None:
    """One procedure out of many tagged ones has too thin a share to clear ``MIN_SUGGESTED_SCORE``."""
    other_rows = [Row(i, ["other"]) for i in range(1, 11)]
    subject_id = _staged(db_session, [Row(0, ["a"]), *other_rows], procs=11)

    assert _support(db_session, subject_id)["a"].score < MIN_SUGGESTED_SCORE


EXTRACTED: dict[str, list[Row]] = {
    "empty": [],
    "single": [Row(0, ["a"])],
    "agree": [Row(0, ["a"]), Row(1, ["a"])],
    "minority": [Row(i, ["a"]) for i in range(4)] + [Row(0, ["b"]), Row(4, ["b"])],
    "boundary": [Row(0, ["a"]), Row(1, ["a"]), Row(2, ["b"]), Row(3, ["b"])],
    "duplicates": [Row(0, ["a"]), Row(0, ["a"]), Row(0, ["a", "a"])],
    "null and empty arrays": [Row(0, ["a"]), Row(1, ["a"]), Row(2, None), Row(3, [])],
    "all untagged": [Row(0), Row(1, [])],
    "three codes": [Row(0, ["a", "b", "c"]), Row(1, ["a", "b"]), Row(2, ["a"])],
    "two of five": [Row(0, ["a"]), Row(1, ["a"]), Row(2, ["b"]), Row(3, ["c"]), Row(4, ["d"])],
    "three of four": [Row(0, ["a"]), Row(1, ["a"]), Row(2, ["a"]), Row(3, ["b"])],
    "split mentions of one procedure": [Row(0, ["a"]), Row(0, ["b"]), Row(1, ["a"])],
    "direct and llm on the same code": [Row(0, ["a"]), Row(1, ["a"], "pvog", 0.6)],
}


def _single_candidate_usable(session: Session, subject_id: uuid.UUID) -> set[str]:
    return {s.code for s in candidate_category_support(session, subject_id) if s.score >= MIN_SUGGESTED_SCORE}


@pytest.mark.parametrize("name", EXTRACTED)
def test_candidate_category_support_agrees_with_the_bulk_completeness_path(db_session: Session, name: str) -> None:
    procs = world.procedures(db_session, 6)
    subject = world.candidate(db_session, procs[0], "subject")
    world.mentioned(db_session, subject, procs, EXTRACTED[name])

    bulk = world.flags_of(db_session)[subject.id]

    assert _single_candidate_usable(db_session, subject.id) == set(bulk.accepted_category_codes)


MANUAL: dict[str, list[Row]] = {
    "override": [Row(0, ["a"]), Row(1, ["a"]), Row(0, ["b"], MANUAL_EXTRACTOR)],
    "empty manual list": [Row(0, ["a"]), Row(1, ["a"]), Row(0, [], MANUAL_EXTRACTOR)],
    "null manual list": [Row(0, ["a"]), Row(1, ["a"]), Row(0, None, MANUAL_EXTRACTOR)],
    "union over procedures": [
        Row(0, ["a"], MANUAL_EXTRACTOR),
        Row(1, ["b"], MANUAL_EXTRACTOR),
        Row(1, ["a"], MANUAL_EXTRACTOR),
    ],
    "manual repeats a code": [Row(0, ["a"]), Row(1, ["a"]), Row(0, ["a"], MANUAL_EXTRACTOR)],
}


@pytest.mark.parametrize("name", MANUAL)
def test_the_python_engine_and_the_bulk_sql_agree_on_manual_fixtures(db_session: Session, name: str) -> None:
    procs = world.procedures(db_session, 6)
    subject = world.candidate(db_session, procs[0], "subject")
    world.mentioned(db_session, subject, procs, MANUAL[name])

    suggestions = candidate_category_suggestions(db_session, subject.id)
    sql = world.flags_of(db_session)[subject.id]

    assert set(usable_codes(suggestions)) == set(sql.accepted_category_codes)


def test_candidate_category_leaf_codes_is_empty_without_any_pvog_mention(db_session: Session) -> None:
    subject_id = _staged(db_session, [Row(0, ["moving-house"])])

    assert candidate_category_leaf_codes(db_session, subject_id) == {}


def test_candidate_category_leaf_codes_maps_each_category_to_its_leaf(db_session: Session) -> None:
    rows = [
        Row(0, ["moving-house", "renting-home"], "pvog", 0.65, "1050200"),
        Row(1, ["retirement"], "llm"),
    ]
    subject_id = _staged(db_session, rows, procs=2)

    assert candidate_category_leaf_codes(db_session, subject_id) == {
        "moving-house": "1050200",
        "renting-home": "1050200",
    }


def test_candidate_category_leaf_codes_takes_the_first_leaf_deterministically_when_leaves_disagree(
    db_session: Session,
) -> None:
    """Rare: two PVOG mentions assert the same category with different leaves; the first, sorted, wins."""
    rows = [
        Row(0, ["illness-care"], "pvog", 0.65, "1130100"),
        Row(1, ["illness-care"], "pvog", 0.95, "1130200"),
    ]
    subject_id = _staged(db_session, rows, procs=2)

    assert candidate_category_leaf_codes(db_session, subject_id) == {"illness-care": "1130100"}
