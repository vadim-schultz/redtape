"""Coverage delta the situation axis would gain under alternative consensus thresholds (chapter 4, situation-tag-coverage).

Pure, DB-free: re-runs the existing, unmodified ``aggregate_tags`` against already-exported mention data,
so no production code changes to measure the bet LR4 needs numbers for.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import NamedTuple
from uuid import UUID

from app.features.discovery.tags import DEFAULT_MIN_PROCEDURES, DEFAULT_MIN_SHARE, TaggedMention, aggregate_tags


class ThresholdVariant(NamedTuple):
    """One situation-axis consensus rule to measure: a label plus the two ``aggregate_tags`` thresholds."""

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


def _covered_candidates(candidates: Mapping[UUID, list[TaggedMention]], variant: ThresholdVariant) -> set[UUID]:
    return {
        candidate_id
        for candidate_id, mentions in candidates.items()
        if any(support.accepted for support in aggregate_tags(mentions, variant.min_procedures, variant.min_share))
    }


def situation_coverage_by_variant(
    candidates: Mapping[UUID, list[TaggedMention]],
    variants: Sequence[ThresholdVariant] = (BASELINE, RELAXED_SINGLE_PROCEDURE),
) -> list[VariantCoverage]:
    """Return each variant's accepted-candidate count and its delta over ``BASELINE``'s covered set."""
    baseline_covered = _covered_candidates(candidates, BASELINE)
    coverage = []
    for variant in variants:
        covered = _covered_candidates(candidates, variant)
        coverage.append(VariantCoverage(variant.name, len(covered), len(covered - baseline_covered)))
    return coverage
