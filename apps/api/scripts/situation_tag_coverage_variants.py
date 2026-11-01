"""Coverage delta the situation axis would gain under alternative consensus thresholds (chapter 4, situation-tag-coverage).

Pure, DB-free: re-runs a frozen snapshot of the old pure-Python consensus rule against already-exported
mention data, so no production code changes to measure the bet LR4 needs numbers for. ``situation-tag-
activation`` chapter 1 later merged that rule into the SQL engine and deleted its production copy; this
tool keeps its own, since it exists to reproduce a point-in-time measurement, not to track the engine.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import NamedTuple
from uuid import UUID

DEFAULT_MIN_PROCEDURES = 2
DEFAULT_MIN_SHARE = 0.5

ExportedMention = tuple[UUID, Sequence[str] | None]
"""A mention as plain data: the procedure (catalogue row) it came from and the codes it carries."""


class ThresholdVariant(NamedTuple):
    """One situation-axis consensus rule to measure: a label plus the two frozen-rule thresholds."""

    name: str
    min_procedures: int
    min_share: float


BASELINE = ThresholdVariant("baseline (2 procedures, 50% share)", DEFAULT_MIN_PROCEDURES, DEFAULT_MIN_SHARE)
RELAXED_SINGLE_PROCEDURE = ThresholdVariant("relaxed (1 procedure, 50% share)", 1, DEFAULT_MIN_SHARE)


class VariantCoverage(NamedTuple):
    """How many candidates a variant covers, and how many of those baseline did not already cover."""

    variant: str
    accepted_candidates: int
    newly_covered_candidates: int


def _accepts_any_code(mentions: list[ExportedMention], min_procedures: int, min_share: float) -> bool:
    by_code: dict[str, set[UUID]] = defaultdict(set)
    for procedure_id, codes in mentions:
        for code in codes or ():
            by_code[code].add(procedure_id)
    if not by_code:
        return False
    tagged = len(set().union(*by_code.values()))
    return any(len(ids) >= min_procedures and len(ids) / tagged >= min_share for ids in by_code.values())


def _covered_candidates(candidates: Mapping[UUID, list[ExportedMention]], variant: ThresholdVariant) -> set[UUID]:
    return {
        candidate_id
        for candidate_id, mentions in candidates.items()
        if _accepts_any_code(mentions, variant.min_procedures, variant.min_share)
    }


def situation_coverage_by_variant(
    candidates: Mapping[UUID, list[ExportedMention]],
    variants: Sequence[ThresholdVariant] = (BASELINE, RELAXED_SINGLE_PROCEDURE),
) -> list[VariantCoverage]:
    """Return each variant's accepted-candidate count and its delta over ``BASELINE``'s covered set."""
    baseline_covered = _covered_candidates(candidates, BASELINE)
    coverage = []
    for variant in variants:
        covered = _covered_candidates(candidates, variant)
        coverage.append(VariantCoverage(variant.name, len(covered), len(covered - baseline_covered)))
    return coverage
