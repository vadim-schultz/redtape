"""The sql tag consensus and manual override equal the python rule (chapter 2, decisions D6 and D18)."""

from __future__ import annotations

from uuid import UUID

import pytest
from app.config import settings
from app.features.discovery.candidate_tags import accepted_codes, candidate_tag_suggestions
from app.features.discovery.repository.candidate_completeness import TagThresholds
from app.features.discovery.tags import aggregate_tags
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


def _python_accepted(mentions: list[tuple[UUID, list[str] | None]], thresholds: TagThresholds) -> set[str]:
    supports = aggregate_tags(mentions, thresholds.min_procedures, thresholds.min_share)
    return {support.code for support in supports if support.accepted}


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


@pytest.mark.parametrize("thresholds", THRESHOLDS)
@pytest.mark.parametrize("name", EXTRACTED)
def test_sql_consensus_matches_aggregate_tags(db_session: Session, name: str, thresholds: TagThresholds) -> None:
    rows = EXTRACTED[name]
    procs = world.procedures(db_session, 6)
    tagged = [(procs[r.procedure].id, r.domains, r.situations) for r in rows]
    expected = (
        _python_accepted([(p, d) for p, d, _ in tagged], thresholds),
        _python_accepted([(p, s) for p, _, s in tagged], thresholds),
    )

    assert _accepted(db_session, rows, thresholds) == expected


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
def test_the_python_rule_and_the_sql_agree_on_manual_fixtures(
    db_session: Session, monkeypatch: pytest.MonkeyPatch, name: str, thresholds: TagThresholds
) -> None:
    monkeypatch.setattr(settings, "discovery_tag_min_procedures", thresholds.min_procedures)
    monkeypatch.setattr(settings, "discovery_tag_min_share", thresholds.min_share)
    procs = world.procedures(db_session, 6)
    subject = world.candidate(db_session, procs[0], "subject")
    world.mentioned(db_session, subject, procs, MANUAL[name])
    db_session.refresh(subject)

    suggestions = candidate_tag_suggestions(subject.mentions)
    sql = world.flags_of(db_session, thresholds)[subject.id]

    assert set(accepted_codes(suggestions.domains)) == set(sql.accepted_domain_codes)
    assert set(accepted_codes(suggestions.situations)) == set(sql.accepted_situation_codes)
