"""Consensus ceiling: how many candidates could ever clear the 2-procedure floor (situation-tag-coverage chapter 2)."""

from __future__ import annotations

import uuid

import pytest
from app.features.discovery.consensus_ceiling import (
    ConsensusCeiling,
    consensus_ceiling,
    procedure_counts_by_candidate,
)

C1, C2, C3, C4 = (uuid.uuid4() for _ in range(4))
P1, P2, P3 = (uuid.uuid4() for _ in range(3))


def test_procedure_counts_by_candidate_counts_distinct_procedures_not_mentions() -> None:
    mentions = [(C1, P1), (C1, P1), (C1, P2), (C2, P1)]

    assert procedure_counts_by_candidate(mentions) == {C1: 2, C2: 1}


def test_consensus_ceiling_buckets_candidates_by_whether_they_can_ever_clear_the_floor() -> None:
    mentions = [(C1, P1), (C1, P2), (C2, P1), (C3, P1), (C3, P2), (C3, P3)]

    result = consensus_ceiling([C1, C2, C3, C4], mentions)

    assert result == ConsensusCeiling(total_candidates=4, at_or_above_floor=2, exactly_one=1, zero=1)


def test_a_candidate_absent_from_mentions_counts_as_zero_not_as_a_missing_key() -> None:
    ceiling = consensus_ceiling([C1, C4], [(C1, P1), (C1, P2)])

    assert (ceiling.at_or_above_floor, ceiling.zero) == (1, 1)


def test_consensus_ceiling_shares_divide_by_the_full_candidate_universe() -> None:
    mentions = [(C1, P1), (C1, P2), (C2, P1), (C3, P1), (C3, P2), (C3, P3)]

    ceiling = consensus_ceiling([C1, C2, C3, C4], mentions)

    assert ceiling.share_at_or_above_floor == pytest.approx(0.5)
    assert ceiling.share_zero == pytest.approx(0.25)


def test_an_empty_candidate_universe_has_full_shares_not_a_division_by_zero() -> None:
    ceiling = consensus_ceiling([], [])

    assert ceiling == ConsensusCeiling(0, 0, 0, 0)
    assert ceiling.share_at_or_above_floor == 0.0
    assert ceiling.share_exactly_one == 0.0
    assert ceiling.share_zero == 0.0


def test_the_default_floor_is_two_procedures_matching_tags_pys_consensus_rule() -> None:
    assert consensus_ceiling([C1], [(C1, P1), (C1, P2)]).at_or_above_floor == 1

    below_floor = consensus_ceiling([C1], [(C1, P1)])
    assert below_floor.at_or_above_floor == 0
    assert below_floor.exactly_one == 1
