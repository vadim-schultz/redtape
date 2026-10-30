"""Completeness read model: five flags, their count, the order, and the manual override (chapter 2)."""

from __future__ import annotations

import pytest
from app.config import settings
from app.features.discovery.repository import DiscoveryRepository
from app.features.discovery.repository.candidate_completeness import (
    TagThresholds,
    completeness_columns,
    completeness_order,
    completeness_subquery,
)
from app.models.discovery import DiscoveryArtifactKind, DiscoveryCandidateMention
from app.shared.list_query import SortOrder
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import completeness_world as world
from completeness_world import Row

SNAPSHOT, SCREENSHOT = DiscoveryArtifactKind.HTML_SNAPSHOT, DiscoveryArtifactKind.SCREENSHOT
TAGGED = Row(0, ["housing"], ["moving-house"])


def _subject(session: Session, procs: int = 2) -> tuple[list, object]:
    procedures = world.procedures(session, procs)
    return procedures, world.candidate(session, procedures[0], "meldebescheinigung")


def test_a_candidate_with_every_signal_is_complete(db_session: Session) -> None:
    procs, subject = _subject(db_session)
    other = world.candidate(db_session, procs[0], "personalausweis")
    world.mentioned(db_session, subject, procs, [TAGGED, TAGGED._replace(procedure=1)])
    world.edge(db_session, other, subject)
    world.artifact(db_session, procs[1], SNAPSHOT)
    world.artifact(db_session, procs[1], SCREENSHOT)

    result = world.flags_of(db_session)[subject.id]

    assert (result.has_domain, result.has_situation, result.has_edges) == (True, True, True)
    assert (result.has_snapshot, result.has_screenshot) == (True, True)
    assert (result.completeness, result.complete) == (5, True)


def test_a_candidate_with_nothing_is_zero(db_session: Session) -> None:
    procs, subject = _subject(db_session, 1)
    world.mentioned(db_session, subject, procs, [Row(0)])

    result = world.flags_of(db_session)[subject.id]

    assert not any((result.has_domain, result.has_situation, result.has_edges))
    assert not any((result.has_snapshot, result.has_screenshot, result.complete))
    assert (result.completeness, result.accepted_domain_codes) == (0, ())


def test_a_single_procedure_never_reaches_the_tag_consensus(db_session: Session) -> None:
    procs, subject = _subject(db_session, 1)
    world.mentioned(db_session, subject, procs, [Row(0, ["housing"])])

    result = world.flags_of(db_session)[subject.id]

    assert result.has_domain is False
    assert result.accepted_domain_codes == ()


def test_edges_count_on_either_end(db_session: Session) -> None:
    procs, parent = _subject(db_session, 1)
    required = world.candidate(db_session, procs[0], "personalausweis")
    lonely = world.candidate(db_session, procs[0], "reisepass")
    world.edge(db_session, parent, required)

    flags = world.flags_of(db_session)

    assert (flags[parent.id].has_edges, flags[required.id].has_edges) == (True, True)
    assert flags[lonely.id].has_edges is False


def test_artifacts_count_only_on_a_mentioning_procedure(db_session: Session) -> None:
    procs, subject = _subject(db_session, 3)
    world.mentioned(db_session, subject, procs[:2], [Row(0), Row(1)])
    world.artifact(db_session, procs[2], SNAPSHOT)
    world.artifact(db_session, procs[2], SCREENSHOT)
    assert world.flags_of(db_session)[subject.id].completeness == 0

    world.artifact(db_session, procs[1], SNAPSHOT)

    result = world.flags_of(db_session)[subject.id]
    assert (result.has_snapshot, result.has_screenshot) == (True, False)


def test_completeness_order_is_completeness_then_mentions(db_session: Session) -> None:
    procs = world.procedures(db_session, 2)
    bare, busy, done = (world.candidate(db_session, procs[0], key) for key in ("bare", "busy", "done"))
    world.mentioned(db_session, bare, procs, [Row(0)])
    world.mentioned(db_session, busy, procs, [Row(0), Row(1), Row(0)])
    world.mentioned(db_session, done, procs, [Row(0)])
    world.artifact(db_session, procs[0], SNAPSHOT)

    sub = completeness_subquery(world.DEFAULTS)
    counts = (
        select(DiscoveryCandidateMention.candidate_id, func.count().label("n"))
        .group_by(DiscoveryCandidateMention.candidate_id)
        .subquery()
    )
    stmt = select(sub.c.candidate_id).outerjoin(counts, counts.c.candidate_id == sub.c.candidate_id)
    stmt = stmt.order_by(*completeness_order(sub, func.coalesce(counts.c.n, 0), SortOrder.DESC))
    ordered = [row[0] for row in db_session.execute(stmt.where(sub.c.candidate_id.in_([bare.id, busy.id, done.id])))]

    assert ordered == [busy.id, done.id, bare.id]
    assert completeness_columns(sub)[0] is sub.c.candidate_id


def test_a_manual_mention_overrides_the_consensus_for_its_axis(db_session: Session) -> None:
    procs, subject = _subject(db_session)
    rows = [Row(0, ["housing"]), Row(1, ["housing"]), Row(0, ["work-employment"], None, "manual")]
    world.mentioned(db_session, subject, procs, rows)

    result = world.flags_of(db_session)[subject.id]

    assert result.accepted_domain_codes == ("work-employment",)
    assert result.has_domain is True


def test_one_manual_mention_on_one_procedure_is_enough(db_session: Session) -> None:
    procs, subject = _subject(db_session, 1)
    world.mentioned(db_session, subject, procs, [Row(0, ["housing"], ["moving-house"], "manual")])

    result = world.flags_of(db_session)[subject.id]

    assert (result.has_domain, result.has_situation) == (True, True)


def test_the_override_is_per_axis(db_session: Session) -> None:
    procs, subject = _subject(db_session, 1)
    world.mentioned(db_session, subject, procs, [Row(0, ["housing"], None, "manual"), Row(0, None, ["moving-house"])])

    result = world.flags_of(db_session)[subject.id]

    assert (result.has_domain, result.has_situation) == (True, False)


@pytest.mark.parametrize("codes", [None, []])
def test_an_empty_manual_code_list_overrides_nothing(db_session: Session, codes: list[str] | None) -> None:
    procs, subject = _subject(db_session)
    world.mentioned(
        db_session, subject, procs, [Row(0, ["housing"]), Row(1, ["housing"]), Row(0, codes, None, "manual")]
    )

    assert world.flags_of(db_session)[subject.id].accepted_domain_codes == ("housing",)


def test_manual_rows_never_leak_to_other_candidates(db_session: Session) -> None:
    procs, curated = _subject(db_session, 1)
    other = world.candidate(db_session, procs[0], "personalausweis")
    world.mentioned(db_session, curated, procs, [Row(0, ["housing"], ["moving-house"], "manual")])
    world.mentioned(db_session, other, procs, [Row(0, ["work-employment"])])

    result = world.flags_of(db_session)[other.id]

    assert (result.has_domain, result.has_situation, result.accepted_domain_codes) == (False, False, ())


def test_thresholds_come_from_settings(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    procs, subject = _subject(db_session, 1)
    world.mentioned(db_session, subject, procs, [Row(0, ["housing"])])
    assert DiscoveryRepository(db_session).completeness_for([subject.id])[subject.id].has_domain is False

    monkeypatch.setattr(settings, "discovery_tag_min_procedures", 1)
    monkeypatch.setattr(settings, "discovery_tag_min_share", 0.75)

    assert TagThresholds.from_settings(settings) == TagThresholds(1, 0.75)
    assert DiscoveryRepository(db_session).completeness_for([subject.id])[subject.id].has_domain is True
