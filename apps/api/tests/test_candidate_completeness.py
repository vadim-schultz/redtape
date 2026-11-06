"""Completeness read model: four flags, their count, the order, and the manual override (chapter 2)."""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

import pytest
from app.features.discovery.repository import candidate_completeness
from app.features.discovery.repository.candidate_completeness import (
    completeness_columns,
    completeness_order,
    completeness_subquery,
)
from app.features.discovery.tags import MIN_SUGGESTED_SCORE, llm_evidence_score
from app.main import create_app
from app.models.discovery import DiscoveryArtifactKind, DiscoveryCandidateMention
from app.shared.list_query import SortOrder
from litestar import Litestar
from litestar.testing import TestClient
from scripts.seed_taxonomy import seed_canonical_taxonomy
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import completeness_world as world
from completeness_world import Row

SNAPSHOT, SCREENSHOT = DiscoveryArtifactKind.HTML_SNAPSHOT, DiscoveryArtifactKind.SCREENSHOT
TAGGED = Row(0, ["housing"])
URL = "/api/v1/candidates"
HOUSING, MOVING, WORK, RETIRE = "home-and-housing", "moving-house", "work-and-employment", "retirement"
PARITY_PROCEDURES = 7
PARITY_ARTIFACTS = {4: (SNAPSHOT, SCREENSHOT), 5: (SNAPSHOT,), 6: (SCREENSHOT,)}


class Member(NamedTuple):
    """One candidate of the parity world: its mentions as (procedure index, codes) and the candidates it requires."""

    key: str
    mentions: tuple[tuple[int, tuple[str, ...] | None], ...] = ()
    requires: tuple[str, ...] = ()


PARITY_WORLD = (
    Member("alpha", ((0, (HOUSING, MOVING)), (1, (HOUSING, MOVING)), (4, None)), requires=("hotel",)),
    Member("bravo", ((0, (HOUSING, MOVING)), (1, (HOUSING, MOVING)), (2, (HOUSING, MOVING)))),
    Member("charlie", ((0, (HOUSING,)), (1, (HOUSING,)), (2, (HOUSING,)), (3, (HOUSING,)))),
    Member("delta", ((3, (WORK,)), (2, (WORK,))), requires=("hotel",)),
    Member("echo", ((6, (RETIRE,)),)),
    Member("foxtrot", ((5, None),)),
    Member("golf"),
    Member("hotel", ((1, (WORK,)),)),
    Member("india", ((0, (HOUSING,)), (4, None)), requires=("hotel",)),
)


class Expected(NamedTuple):
    """The four-flag reading of one candidate: its flag count, whether all four hold, its confidence and mentions."""

    completeness: int
    complete: bool
    confidence: float
    mentions: int


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    seed_canonical_taxonomy(db_session)
    monkeypatch.setattr("app.main.provide_session", lambda: db_session)
    with TestClient(create_app()) as test_client:
        yield test_client


def _build_parity_world(session: Session) -> None:
    procs = world.procedures(session, PARITY_PROCEDURES)
    owners = {member.key: world.candidate(session, procs[0], member.key) for member in PARITY_WORLD}
    for member in PARITY_WORLD:
        world.mentioned(session, owners[member.key], procs, [Row(index, codes) for index, codes in member.mentions])
        for required in member.requires:
            world.edge(session, owners[member.key], owners[required])
    for index, kinds in PARITY_ARTIFACTS.items():
        for kind in kinds:
            world.artifact(session, procs[index], kind)


def _procedures_with(member: Member, code: str) -> int:
    return len({index for index, codes in member.mentions if codes and code in codes})


def _category_scores(member: Member) -> dict[str, float]:
    """Score every code with the LLM evidence curve over its share of the procedures that carry any code."""
    tagged = len({index for index, codes in member.mentions if codes})
    codes = {code for _, row_codes in member.mentions for code in row_codes or ()}
    scores: dict[str, float] = {}
    for code in codes:
        procedures = _procedures_with(member, code)
        scores[code] = llm_evidence_score(procedures, procedures / tagged)
    return scores


def _artifact_kinds(member: Member) -> set[DiscoveryArtifactKind]:
    return {kind for index, _ in member.mentions for kind in PARITY_ARTIFACTS.get(index, ())}


def _expected(member: Member, members: tuple[Member, ...]) -> Expected:
    """Apply the four-flag rule to one member of the world, from its definition and not from the database."""
    scores = _category_scores(member)
    kinds = _artifact_kinds(member)
    has_edges = bool(member.requires) or any(member.key in other.requires for other in members)
    flags = (
        any(score >= MIN_SUGGESTED_SCORE for score in scores.values()),
        has_edges,
        SNAPSHOT in kinds,
        SCREENSHOT in kinds,
    )
    return Expected(
        completeness=sum(flags),
        complete=all(flags),
        confidence=max(scores.values(), default=0.0),
        mentions=len(member.mentions),
    )


def _expected_world() -> dict[str, Expected]:
    return {member.key: _expected(member, PARITY_WORLD) for member in PARITY_WORLD}


def _completeness_rank(value: Expected) -> tuple[int, int]:
    return (-value.completeness, -value.mentions)


def _default_order(expected: dict[str, Expected]) -> list[str]:
    """Confidence, then completeness, then mentions, all best first; the key breaks the rest (titles equal keys)."""
    return sorted(expected, key=lambda key: (-expected[key].confidence, *_completeness_rank(expected[key]), key))


def _completeness_order(expected: dict[str, Expected]) -> list[str]:
    return sorted(expected, key=lambda key: (*_completeness_rank(expected[key]), key))


def _public_keys(client: TestClient[Litestar], **params: str) -> list[str]:
    response = client.get(URL, params={"limit": 100, **params})
    assert response.status_code == 200, response.text
    return [item["key"] for item in response.json()["items"]]


def test_public_order_and_complete_follow_the_four_flag_rule(client: TestClient[Litestar], db_session: Session) -> None:
    _build_parity_world(db_session)
    expected = _expected_world()

    complete = set(_public_keys(client, **{"filter[complete]": "yes"}))

    assert complete == {key for key, value in expected.items() if value.complete}
    assert set(_public_keys(client, **{"filter[complete]": "no"})) == set(expected) - complete
    assert _public_keys(client) == _default_order(expected)
    assert _public_keys(client, sort_by="completeness", sort_order="desc") == _completeness_order(expected)


@pytest.mark.parametrize("value", ["maybe", "true"])
def test_an_invalid_complete_value_answers_422_naming_the_parameter(
    client: TestClient[Litestar], db_session: Session, value: str
) -> None:
    _build_parity_world(db_session)

    response = client.get(URL, params={"filter[complete]": value})

    assert response.status_code == 422
    assert "filter[complete]" in str(response.json())


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

    assert (result.has_category, result.has_edges) == (True, True)
    assert (result.has_snapshot, result.has_screenshot) == (True, True)
    assert (result.completeness, result.complete) == (4, True)


def test_a_candidate_with_nothing_is_zero(db_session: Session) -> None:
    procs, subject = _subject(db_session, 1)
    world.mentioned(db_session, subject, procs, [Row(0)])

    result = world.flags_of(db_session)[subject.id]

    assert not any((result.has_category, result.has_edges, result.has_snapshot, result.has_screenshot))
    assert (result.completeness, result.complete, result.accepted_category_codes) == (0, False, ())


def test_a_single_llm_mention_with_a_category_sets_the_category_flag(db_session: Session) -> None:
    """A lone LLM mention carrying a category clears the inclusion floor, so the category flag holds."""
    procs, subject = _subject(db_session, 1)
    world.mentioned(db_session, subject, procs, [Row(0, ["housing", "moving-house"])])

    result = world.flags_of(db_session)[subject.id]

    assert result.has_category is True
    assert result.accepted_category_codes == ("housing", "moving-house")


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
    world.mentioned(db_session, bare, procs, [Row(1)] * 4)
    world.mentioned(db_session, busy, procs, [Row(0), Row(1), Row(0)])
    world.mentioned(db_session, done, procs, [Row(0)])
    world.artifact(db_session, procs[0], SNAPSHOT)

    sub = completeness_subquery()
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


def test_a_manual_mention_overrides_the_consensus_for_categories(db_session: Session) -> None:
    procs, subject = _subject(db_session)
    rows = [Row(0, ["housing"]), Row(1, ["housing"]), Row(0, ["work-employment"], "manual")]
    world.mentioned(db_session, subject, procs, rows)

    result = world.flags_of(db_session)[subject.id]

    assert result.accepted_category_codes == ("work-employment",)
    assert result.has_category is True


def test_one_manual_mention_on_one_procedure_is_enough(db_session: Session) -> None:
    procs, subject = _subject(db_session, 1)
    world.mentioned(db_session, subject, procs, [Row(0, ["housing", "moving-house"], "manual")])

    result = world.flags_of(db_session)[subject.id]

    assert (result.has_category, result.accepted_category_codes) == (True, ("housing", "moving-house"))


@pytest.mark.parametrize("codes", [None, []])
def test_an_empty_manual_code_list_overrides_nothing(db_session: Session, codes: list[str] | None) -> None:
    procs, subject = _subject(db_session)
    world.mentioned(db_session, subject, procs, [Row(0, ["housing"]), Row(1, ["housing"]), Row(0, codes, "manual")])

    assert world.flags_of(db_session)[subject.id].accepted_category_codes == ("housing",)


def test_manual_rows_never_leak_to_other_candidates(db_session: Session) -> None:
    procs, curated = _subject(db_session, 1)
    other = world.candidate(db_session, procs[0], "personalausweis")
    world.mentioned(db_session, curated, procs, [Row(0, ["housing"], "manual")])
    world.mentioned(db_session, other, procs, [Row(0, ["work-employment"])])

    result = world.flags_of(db_session)[other.id]

    assert result.accepted_category_codes == ("work-employment",)
    assert result.has_category is True


PUBLIC_PRESENTATION = ("app.schema.candidate", "app.features.candidates", "app.schema.discovery.read")


def test_internal_completeness_imports_no_public_presentation_module() -> None:
    """Removing a public tag or checklist field cannot change the flags: the read model never imports one."""
    tree = ast.parse(Path(candidate_completeness.__file__).read_text(encoding="utf-8"))
    imported = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}

    assert [m for m in imported if m.startswith(PUBLIC_PRESENTATION)] == []
