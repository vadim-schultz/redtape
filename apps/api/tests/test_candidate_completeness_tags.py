"""One consensus engine in SQL, shared by the bulk completeness path and the single-candidate detail path.

Chapter 1 merges the two pure-Python consensus helpers this module's predecessor tests once exercised
(since deleted) into this module's ``code_support``/``_manual_support``, wrapped by ``candidate_axis_
support`` for one candidate. These tests port that deleted pair's own regression cases onto
``candidate_axis_support`` directly, then pin the two paths' agreement so a future change that breaks it
is caught immediately (decisions D6, D18, D3).
"""

from __future__ import annotations

import uuid

import pytest
from app.config import settings
from app.features.discovery.candidate_tags import accepted_codes, candidate_tag_suggestions
from app.features.discovery.repository.candidate_completeness import TagThresholds
from app.features.discovery.repository.candidate_completeness_tags import candidate_axis_support
from app.features.discovery.tags import MANUAL_EXTRACTOR, TagAxis, TagSupport
from sqlalchemy.orm import Session

import completeness_world as world
from completeness_world import Row


def _accepted(session: Session, rows: list[Row], thresholds: TagThresholds = world.DEFAULTS) -> tuple[set, set]:
    procs = world.procedures(session, 6)
    subject = world.candidate(session, procs[0], "subject")
    world.mentioned(session, subject, procs, rows)
    result = world.flags_of(session, thresholds)[subject.id]
    return set(result.accepted_domain_codes), set(result.accepted_situation_codes)


def test_the_share_rule_excludes_a_minority_code(db_session: Session) -> None:
    rows = [Row(i, ["a"]) for i in range(4)] + [Row(0, ["b"]), Row(4, ["b"])]

    assert _accepted(db_session, rows)[0] == {"a"}


def test_untagged_mentions_do_not_dilute_the_share(db_session: Session) -> None:
    rows = [Row(0, ["a"]), Row(1, ["a"]), Row(2), Row(3), Row(4, [], [])]

    assert _accepted(db_session, rows)[0] == {"a"}


def test_a_duplicate_mention_on_one_procedure_counts_once(db_session: Session) -> None:
    assert _accepted(db_session, [Row(0, ["a"]), Row(0, ["a"])])[0] == set()


def test_the_share_boundary_is_inclusive(db_session: Session) -> None:
    rows = [Row(0, ["a"]), Row(1, ["a"]), Row(2, ["b"]), Row(3, ["b"])]

    assert _accepted(db_session, rows)[0] == {"a", "b"}


def test_a_share_just_below_the_boundary_is_not_accepted(db_session: Session) -> None:
    rows = [Row(0, ["a"]), Row(1, ["a"]), Row(2, ["b"]), Row(3, ["b"]), Row(4, ["b"])]

    assert _accepted(db_session, rows)[0] == {"b"}


def _domain_support(session: Session, subject_id: uuid.UUID, thresholds: TagThresholds) -> dict[str, TagSupport]:
    supports = candidate_axis_support(session, subject_id, TagAxis.DOMAIN, thresholds)
    return {support.code: support for support in supports}


def _staged(session: Session, rows: list[Row], procs: int = 2) -> uuid.UUID:
    procedures = world.procedures(session, procs)
    subject = world.candidate(session, procedures[0], "subject")
    world.mentioned(session, subject, procedures, rows)
    return subject.id


def test_candidate_axis_support_counts_distinct_procedures_not_mentions(db_session: Session) -> None:
    rows = [Row(0, ["housing"]), Row(0, ["housing"]), Row(0, ["housing", "work"]), Row(1, ["housing"])]
    subject_id = _staged(db_session, rows)

    result = _domain_support(db_session, subject_id, world.DEFAULTS)

    assert result["housing"] == TagSupport("housing", procedures=2, share=1.0, accepted=True)
    assert result["work"] == TagSupport("work", procedures=1, share=0.5, accepted=False)


def test_candidate_axis_support_accepts_a_code_at_exactly_two_procedures_and_fifty_percent(
    db_session: Session,
) -> None:
    rows = [Row(0, ["a"]), Row(1, ["a"]), Row(2, ["b"]), Row(3, ["b"])]
    subject_id = _staged(db_session, rows, procs=4)

    result = _domain_support(db_session, subject_id, world.DEFAULTS)

    assert result["a"] == TagSupport("a", procedures=2, share=0.5, accepted=True)


def test_candidate_axis_support_does_not_accept_a_code_seen_on_one_procedure(db_session: Session) -> None:
    subject_id = _staged(db_session, [Row(0, ["housing"]), Row(0, ["housing"])], procs=1)

    result = candidate_axis_support(db_session, subject_id, TagAxis.DOMAIN, world.DEFAULTS)

    assert result == [TagSupport("housing", procedures=1, share=1.0, accepted=False)]


def test_candidate_axis_support_does_not_accept_a_code_below_the_share(db_session: Session) -> None:
    rows = [Row(0, ["a"]), Row(1, ["a"]), Row(2, ["b"]), Row(3, ["b"]), Row(4, ["b"])]
    subject_id = _staged(db_session, rows, procs=5)

    result = _domain_support(db_session, subject_id, world.DEFAULTS)

    assert result["a"].accepted is False
    assert result["a"].share == pytest.approx(0.4)
    assert result["b"].accepted is True


def test_candidate_axis_support_ignores_mentions_without_codes_in_the_share(db_session: Session) -> None:
    rows = [Row(0, ["a"]), Row(1, ["a"]), Row(2, None), Row(3, [])]
    subject_id = _staged(db_session, rows, procs=4)

    assert candidate_axis_support(db_session, subject_id, TagAxis.DOMAIN, world.DEFAULTS) == [
        TagSupport("a", procedures=2, share=1.0, accepted=True)
    ]
    other_id = _staged(db_session, [Row(0, None), Row(1, [])], procs=2)
    assert candidate_axis_support(db_session, other_id, TagAxis.DOMAIN, world.DEFAULTS) == []


def test_candidate_axis_support_thresholds_are_parameters_and_the_result_is_ordered(db_session: Session) -> None:
    rows = [Row(0, ["b", "a"]), Row(1, ["a"])]
    subject_id = _staged(db_session, rows, procs=2)

    result = candidate_axis_support(db_session, subject_id, TagAxis.DOMAIN, TagThresholds(3, 0.5))

    assert [(s.code, s.procedures, s.accepted) for s in result] == [("a", 2, False), ("b", 1, False)]
    loose = candidate_axis_support(db_session, subject_id, TagAxis.DOMAIN, TagThresholds(1, 0.9))
    assert loose[1].accepted is False


def test_candidate_axis_support_manual_mention_takes_one_procedure_and_ignores_the_consensus(
    db_session: Session,
) -> None:
    rows = [Row(0, ["housing"]), Row(1, ["housing"]), Row(0, ["work"], None, MANUAL_EXTRACTOR)]
    subject_id = _staged(db_session, rows, procs=2)

    result = candidate_axis_support(db_session, subject_id, TagAxis.DOMAIN, world.DEFAULTS)

    assert result == [TagSupport("work", procedures=1, share=1.0, accepted=True)]


def test_candidate_axis_support_manual_mentions_union_over_procedures(db_session: Session) -> None:
    rows = [Row(0, ["b", "a"], None, MANUAL_EXTRACTOR), Row(1, ["a"], None, MANUAL_EXTRACTOR)]
    subject_id = _staged(db_session, rows, procs=2)

    result = candidate_axis_support(db_session, subject_id, TagAxis.DOMAIN, world.DEFAULTS)

    assert result == [
        TagSupport("a", procedures=2, share=1.0, accepted=True),
        TagSupport("b", procedures=1, share=1.0, accepted=True),
    ]


def test_candidate_axis_support_is_empty_without_a_manual_mention_carrying_codes(db_session: Session) -> None:
    rows = [Row(0, ["housing"], None, "llm"), Row(0, None, None, MANUAL_EXTRACTOR), Row(0, [], None, MANUAL_EXTRACTOR)]
    subject_id = _staged(db_session, rows, procs=1)

    result = candidate_axis_support(db_session, subject_id, TagAxis.DOMAIN, TagThresholds(1, 0.5))

    assert result == [TagSupport("housing", procedures=1, share=1.0, accepted=True)]


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
}
THRESHOLDS = [TagThresholds(2, 0.5), TagThresholds(1, 0.75)]


def _single_candidate_accepted(session: Session, subject_id: uuid.UUID, thresholds: TagThresholds) -> tuple[set, set]:
    domain = candidate_axis_support(session, subject_id, TagAxis.DOMAIN, thresholds)
    situation = candidate_axis_support(session, subject_id, TagAxis.SITUATION, thresholds)
    return {s.code for s in domain if s.accepted}, {s.code for s in situation if s.accepted}


@pytest.mark.parametrize("thresholds", THRESHOLDS)
@pytest.mark.parametrize("name", EXTRACTED)
def test_candidate_axis_support_agrees_with_the_bulk_completeness_path(
    db_session: Session, name: str, thresholds: TagThresholds
) -> None:
    rows = EXTRACTED[name]
    procs = world.procedures(db_session, 6)
    subject = world.candidate(db_session, procs[0], "subject")
    world.mentioned(db_session, subject, procs, rows)

    bulk = world.flags_of(db_session, thresholds)[subject.id]
    single = _single_candidate_accepted(db_session, subject.id, thresholds)

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


@pytest.mark.parametrize("thresholds", THRESHOLDS)
@pytest.mark.parametrize("name", MANUAL)
def test_the_merged_engine_and_the_bulk_sql_agree_on_manual_fixtures(
    db_session: Session, monkeypatch: pytest.MonkeyPatch, name: str, thresholds: TagThresholds
) -> None:
    monkeypatch.setattr(settings, "discovery_tag_min_procedures", thresholds.min_procedures)
    monkeypatch.setattr(settings, "discovery_tag_min_share", thresholds.min_share)
    procs = world.procedures(db_session, 6)
    subject = world.candidate(db_session, procs[0], "subject")
    world.mentioned(db_session, subject, procs, MANUAL[name])

    suggestions = candidate_tag_suggestions(db_session, subject.id)
    sql = world.flags_of(db_session, thresholds)[subject.id]

    assert set(accepted_codes(suggestions.domains)) == set(sql.accepted_domain_codes)
    assert set(accepted_codes(suggestions.situations)) == set(sql.accepted_situation_codes)
