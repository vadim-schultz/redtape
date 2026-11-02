"""One scoring engine in SQL, shared by the bulk completeness path and the single-candidate detail path.

Chapter 1 of ``situation-tag-hierarchy`` replaces the prior accept/reject ``TagThresholds`` gate with a
continuous score: the LLM-evidence curve combined via noisy-OR with any direct-source confidence. These
tests port the manual-override regression onto the new score (unchanged behaviour), add the new scoring
cases the chapter introduces, and pin the bulk and single-candidate paths' agreement on the inclusion
floor so a future change that breaks it is caught immediately.
"""

from __future__ import annotations

import uuid

import pytest
from app.features.discovery.candidate_tags import candidate_tag_suggestions, usable_codes
from app.features.discovery.repository.candidate_axis_support import candidate_axis_support
from app.features.discovery.repository.candidate_leaf_codes import candidate_situation_leaf_codes
from app.features.discovery.tags import MANUAL_EXTRACTOR, MIN_SUGGESTED_SCORE, TagAxis, TagSupport
from sqlalchemy.orm import Session

import completeness_world as world
from completeness_world import Row


def _domain_support(session: Session, subject_id: uuid.UUID) -> dict[str, TagSupport]:
    supports = candidate_axis_support(session, subject_id, TagAxis.DOMAIN)
    return {support.code: support for support in supports}


def _staged(session: Session, rows: list[Row], procs: int = 2) -> uuid.UUID:
    procedures = world.procedures(session, procs)
    subject = world.candidate(session, procedures[0], "subject")
    world.mentioned(session, subject, procedures, rows)
    return subject.id


def test_candidate_axis_support_counts_distinct_procedures_not_mentions(db_session: Session) -> None:
    rows = [Row(0, ["housing"]), Row(0, ["housing"]), Row(0, ["housing", "work"]), Row(1, ["housing"])]
    subject_id = _staged(db_session, rows)

    result = _domain_support(db_session, subject_id)

    assert (result["housing"].procedures, result["housing"].share) == (2, 1.0)
    assert (result["work"].procedures, result["work"].share) == (1, 0.5)
    assert result["housing"].score > result["work"].score


def test_candidate_axis_support_ignores_mentions_without_codes_in_the_share(db_session: Session) -> None:
    rows = [Row(0, ["a"]), Row(1, ["a"]), Row(2, None), Row(3, [])]
    subject_id = _staged(db_session, rows, procs=4)

    result = candidate_axis_support(db_session, subject_id, TagAxis.DOMAIN)

    assert result == [TagSupport("a", procedures=2, share=1.0, score=pytest.approx(0.85))]
    other_id = _staged(db_session, [Row(0, None), Row(1, [])], procs=2)
    assert candidate_axis_support(db_session, other_id, TagAxis.DOMAIN) == []


def test_candidate_axis_support_orders_most_supported_code_first(db_session: Session) -> None:
    rows = [Row(0, ["b", "a"]), Row(1, ["a"])]
    subject_id = _staged(db_session, rows, procs=2)

    result = candidate_axis_support(db_session, subject_id, TagAxis.DOMAIN)

    assert [support.code for support in result] == ["a", "b"]
    assert result[0].procedures >= result[1].procedures


def test_candidate_axis_support_manual_mention_takes_one_procedure_and_ignores_the_consensus(
    db_session: Session,
) -> None:
    rows = [Row(0, ["housing"]), Row(1, ["housing"]), Row(0, ["work"], None, MANUAL_EXTRACTOR)]
    subject_id = _staged(db_session, rows, procs=2)

    result = candidate_axis_support(db_session, subject_id, TagAxis.DOMAIN)

    assert result == [TagSupport("work", procedures=1, share=1.0, score=1.0)]


def test_candidate_axis_support_manual_mentions_union_over_procedures(db_session: Session) -> None:
    rows = [Row(0, ["b", "a"], None, MANUAL_EXTRACTOR), Row(1, ["a"], None, MANUAL_EXTRACTOR)]
    subject_id = _staged(db_session, rows, procs=2)

    result = candidate_axis_support(db_session, subject_id, TagAxis.DOMAIN)

    assert result == [
        TagSupport("a", procedures=2, share=1.0, score=1.0),
        TagSupport("b", procedures=1, share=1.0, score=1.0),
    ]


def test_candidate_axis_support_is_empty_without_a_manual_mention_carrying_codes(db_session: Session) -> None:
    rows = [Row(0, ["housing"], None, "llm"), Row(0, None, None, MANUAL_EXTRACTOR), Row(0, [], None, MANUAL_EXTRACTOR)]
    subject_id = _staged(db_session, rows, procs=1)

    result = candidate_axis_support(db_session, subject_id, TagAxis.DOMAIN)

    assert result == [TagSupport("housing", procedures=1, share=1.0, score=pytest.approx(0.5))]


def test_both_axes_score_a_single_procedure_identically(db_session: Session) -> None:
    """D8: the scoring engine no longer special-cases either axis — the regression this chapter creates,
    replacing situation-tag-activation's own regression that a single procedure cleared only the relaxed
    situation floor but not the stricter domain one.
    """
    rows = [Row(0, ["housing"], ["moving-house"])]
    subject_id = _staged(db_session, rows, procs=1)

    suggestions = candidate_tag_suggestions(db_session, subject_id)

    assert usable_codes(suggestions.domains) == ["housing"]
    assert usable_codes(suggestions.situations) == ["moving-house"]
    assert suggestions.domains[0].score == pytest.approx(suggestions.situations[0].score)


def test_a_direct_confidence_mention_combines_with_llm_evidence_via_noisy_or(db_session: Session) -> None:
    """A PVOG-shaped direct assertion and an LLM-extracted one on the same code corroborate: the combined
    score beats either source alone (the noisy-OR this chapter introduces to replace the accept/reject gate).
    """
    llm_only_id = _staged(db_session, [Row(0, ["a"])], procs=1)
    direct_only_id = _staged(db_session, [Row(0, ["a"], None, "pvog", 0.6)], procs=1)
    both_id = _staged(db_session, [Row(0, ["a"]), Row(1, ["a"], None, "pvog", 0.6)], procs=2)

    llm_only = _domain_support(db_session, llm_only_id)["a"].score
    direct_only = _domain_support(db_session, direct_only_id)["a"].score
    both = _domain_support(db_session, both_id)["a"].score

    assert both > llm_only
    assert both > direct_only


def test_a_single_low_share_llm_mention_scores_below_the_inclusion_floor(db_session: Session) -> None:
    """One procedure out of many tagged ones has too thin a share to clear ``MIN_SUGGESTED_SCORE`` (D9)."""
    other_rows = [Row(i, ["other"]) for i in range(1, 11)]
    subject_id = _staged(db_session, [Row(0, ["a"]), *other_rows], procs=11)

    score = _domain_support(db_session, subject_id)["a"].score

    assert score < MIN_SUGGESTED_SCORE


EXTRACTED: dict[str, list[Row]] = {
    "empty": [],
    "single": [Row(0, ["a"], ["x"])],
    "agree": [Row(0, ["a"], ["x"]), Row(1, ["a"], ["x"])],
    "minority": [Row(i, ["a"]) for i in range(4)] + [Row(0, ["b"]), Row(4, ["b"])],
    "boundary": [Row(0, ["a"]), Row(1, ["a"]), Row(2, ["b"]), Row(3, ["b"])],
    "duplicates": [Row(0, ["a"]), Row(0, ["a"]), Row(0, ["a", "a"])],
    "null and empty arrays": [Row(0, ["a"]), Row(1, ["a"]), Row(2, None), Row(3, [])],
    "all untagged": [Row(0), Row(1, [], [])],
    "three codes": [Row(0, ["a", "b", "c"]), Row(1, ["a", "b"]), Row(2, ["a"])],
    "two of five": [Row(0, ["a"]), Row(1, ["a"]), Row(2, ["b"]), Row(3, ["c"]), Row(4, ["d"])],
    "three of four": [Row(0, ["a"]), Row(1, ["a"]), Row(2, ["a"]), Row(3, ["b"])],
    "split mentions of one procedure": [Row(0, ["a"]), Row(0, ["b"]), Row(1, ["a"])],
    "axes differ": [Row(0, ["a"], ["x"]), Row(1, ["a"], ["y"]), Row(2, None, ["y"])],
    "direct and llm on the same code": [Row(0, ["a"]), Row(1, ["a"], None, "pvog", 0.6)],
}


def _single_candidate_usable(session: Session, subject_id: uuid.UUID) -> tuple[set, set]:
    domain = candidate_axis_support(session, subject_id, TagAxis.DOMAIN)
    situation = candidate_axis_support(session, subject_id, TagAxis.SITUATION)
    floor = MIN_SUGGESTED_SCORE
    return {s.code for s in domain if s.score >= floor}, {s.code for s in situation if s.score >= floor}


@pytest.mark.parametrize("name", EXTRACTED)
def test_candidate_axis_support_agrees_with_the_bulk_completeness_path(db_session: Session, name: str) -> None:
    rows = EXTRACTED[name]
    procs = world.procedures(db_session, 6)
    subject = world.candidate(db_session, procs[0], "subject")
    world.mentioned(db_session, subject, procs, rows)

    bulk = world.flags_of(db_session)[subject.id]
    single = _single_candidate_usable(db_session, subject.id)

    assert single == (set(bulk.accepted_domain_codes), set(bulk.accepted_situation_codes))


MANUAL: dict[str, list[Row]] = {
    "override": [Row(0, ["a"]), Row(1, ["a"]), Row(0, ["b"], None, "manual")],
    "empty manual list": [Row(0, ["a"]), Row(1, ["a"]), Row(0, [], [], "manual")],
    "null manual list": [Row(0, ["a"]), Row(1, ["a"]), Row(0, None, None, "manual")],
    "mixed axes": [Row(0, ["a"], ["x"]), Row(1, ["a"], ["x"]), Row(0, ["b"], None, "manual")],
    "union over procedures": [
        Row(0, ["a"], None, "manual"),
        Row(1, ["b"], ["x"], "manual"),
        Row(1, ["a"], None, "manual"),
    ],
    "manual only on situations": [Row(0, ["a"]), Row(1, ["a"]), Row(2, None, ["x"], "manual")],
    "manual repeats a code": [Row(0, ["a"]), Row(1, ["a"]), Row(0, ["a"], None, "manual")],
}


@pytest.mark.parametrize("name", MANUAL)
def test_the_merged_engine_and_the_bulk_sql_agree_on_manual_fixtures(db_session: Session, name: str) -> None:
    procs = world.procedures(db_session, 6)
    subject = world.candidate(db_session, procs[0], "subject")
    world.mentioned(db_session, subject, procs, MANUAL[name])

    suggestions = candidate_tag_suggestions(db_session, subject.id)
    sql = world.flags_of(db_session)[subject.id]

    assert set(usable_codes(suggestions.domains)) == set(sql.accepted_domain_codes)
    assert set(usable_codes(suggestions.situations)) == set(sql.accepted_situation_codes)


def test_candidate_situation_leaf_codes_is_empty_without_any_pvog_mention(db_session: Session) -> None:
    subject_id = _staged(db_session, [Row(0, None, ["moving-house"])])

    assert candidate_situation_leaf_codes(db_session, subject_id) == {}


def test_candidate_situation_leaf_codes_maps_each_situation_code_to_its_leaf(db_session: Session) -> None:
    rows = [
        Row(0, None, ["moving-house", "renting-home"], "pvog", None, 0.65, "1050200"),
        Row(1, None, ["retirement"], "llm"),
    ]
    subject_id = _staged(db_session, rows, procs=2)

    assert candidate_situation_leaf_codes(db_session, subject_id) == {
        "moving-house": "1050200",
        "renting-home": "1050200",
    }


def test_candidate_situation_leaf_codes_takes_the_first_leaf_deterministically_when_leaves_disagree(
    db_session: Session,
) -> None:
    """Rare: two PVOG mentions assert the same situation code with different leaves — take the first,
    sorted, rather than an arbitrary one."""
    rows = [
        Row(0, None, ["illness-care"], "pvog", None, 0.65, "1130100"),
        Row(1, None, ["illness-care"], "pvog", None, 0.95, "1130200"),
    ]
    subject_id = _staged(db_session, rows, procs=2)

    assert candidate_situation_leaf_codes(db_session, subject_id) == {"illness-care": "1130100"}
