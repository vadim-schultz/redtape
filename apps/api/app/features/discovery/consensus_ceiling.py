"""Consensus ceiling: how many candidates have enough distinct procedures to ever clear the consensus floor."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Collection, Iterable
from typing import NamedTuple
from uuid import UUID

HISTORICAL_CONSENSUS_FLOOR_PROCEDURES = 2
"""The historical 2-procedure consensus floor this reporting tool measures candidates against.

Frozen here rather than imported: ``situation-tag-hierarchy`` chapter 1 replaced the accept/reject
floor this constant once fed (``app.features.discovery.tags``) with a continuous score, so this module
keeps its own copy to keep reproducing the same point-in-time measurement, not to track the engine —
the same precedent ``scripts/situation_tag_coverage_variants.py`` already set.
"""

CandidateMention = tuple[UUID, UUID]
"""A mention as plain data: the candidate it was found on and the procedure (catalogue row) that carries it."""


class ConsensusCeiling(NamedTuple):
    """How many of all candidates have enough distinct procedures to ever clear the consensus floor."""

    total_candidates: int
    at_or_above_floor: int
    exactly_one: int
    zero: int

    @property
    def share_at_or_above_floor(self) -> float:
        """Return the share of candidates that clear the floor; 0.0 when there are none."""
        return self.at_or_above_floor / self.total_candidates if self.total_candidates else 0.0

    @property
    def share_exactly_one(self) -> float:
        """Return the share of candidates mentioned by exactly one procedure; 0.0 when none exist."""
        return self.exactly_one / self.total_candidates if self.total_candidates else 0.0

    @property
    def share_zero(self) -> float:
        """Return the share of candidates that no procedure mentions; 0.0 when none exist."""
        return self.zero / self.total_candidates if self.total_candidates else 0.0


def procedure_counts_by_candidate(mentions: Iterable[CandidateMention]) -> dict[UUID, int]:
    """Return the number of distinct procedures that mention each candidate, counting each procedure once."""
    procedures_by_candidate: dict[UUID, set[UUID]] = defaultdict(set)
    for candidate_id, procedure_id in mentions:
        procedures_by_candidate[candidate_id].add(procedure_id)
    return {candidate_id: len(procedures) for candidate_id, procedures in procedures_by_candidate.items()}


def consensus_ceiling(
    candidate_ids: Collection[UUID],
    mentions: Iterable[CandidateMention],
    *,
    min_procedures: int = HISTORICAL_CONSENSUS_FLOOR_PROCEDURES,
) -> ConsensusCeiling:
    """Return how many of candidate_ids have at least min_procedures distinct procedures mentioning them."""
    counts = procedure_counts_by_candidate(mentions)
    at_or_above_floor = exactly_one = zero = 0
    for candidate_id in candidate_ids:
        count = counts.get(candidate_id, 0)
        if count >= min_procedures:
            at_or_above_floor += 1
        elif count == 1:
            exactly_one += 1
        else:
            zero += 1
    return ConsensusCeiling(len(candidate_ids), at_or_above_floor, exactly_one, zero)
