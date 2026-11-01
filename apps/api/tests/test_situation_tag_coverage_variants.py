"""Situation-axis threshold variants: coverage delta a relaxed rule would buy (chapter 4, situation-tag-coverage)."""

from __future__ import annotations

import uuid

from scripts.situation_tag_coverage_variants import BASELINE, RELAXED_SINGLE_PROCEDURE, situation_coverage_by_variant

C1, C2, C3 = (uuid.uuid4() for _ in range(3))
P1, P2, P3 = (uuid.uuid4() for _ in range(3))


def test_baseline_variant_needs_two_procedures_and_half_their_codes_to_agree() -> None:
    candidates = {
        C1: [(P1, ["birth-of-child"])],
        C2: [(P1, ["birth-of-child"]), (P2, ["birth-of-child"])],
        C3: [(P1, ["moving"]), (P2, ["parenthood"])],
    }

    result = situation_coverage_by_variant(candidates, (BASELINE,))

    assert result[0].accepted_candidates == 1


def test_relaxed_single_procedure_variant_covers_a_candidate_with_one_tagging_procedure() -> None:
    candidates = {C1: [(P1, ["birth-of-child"])]}

    result = situation_coverage_by_variant(candidates, (BASELINE, RELAXED_SINGLE_PROCEDURE))

    by_variant = {row.variant: row for row in result}
    assert by_variant[BASELINE.name].accepted_candidates == 0
    assert by_variant[RELAXED_SINGLE_PROCEDURE.name].accepted_candidates == 1
    assert by_variant[RELAXED_SINGLE_PROCEDURE.name].newly_covered_candidates == 1


def test_candidates_already_covered_by_baseline_are_not_counted_as_newly_covered() -> None:
    candidates = {C1: [(P1, ["birth-of-child"]), (P2, ["birth-of-child"])]}

    result = situation_coverage_by_variant(candidates, (BASELINE, RELAXED_SINGLE_PROCEDURE))

    by_variant = {row.variant: row for row in result}
    assert by_variant[RELAXED_SINGLE_PROCEDURE.name].accepted_candidates == 1
    assert by_variant[RELAXED_SINGLE_PROCEDURE.name].newly_covered_candidates == 0


def test_candidate_with_two_situation_codes_from_one_procedure_counts_once() -> None:
    candidates = {C1: [(P1, ["birth-of-child", "moving"])]}

    result = situation_coverage_by_variant(candidates, (BASELINE, RELAXED_SINGLE_PROCEDURE))

    by_variant = {row.variant: row for row in result}
    assert by_variant[RELAXED_SINGLE_PROCEDURE.name].accepted_candidates == 1
    assert by_variant[RELAXED_SINGLE_PROCEDURE.name].newly_covered_candidates == 1


def test_candidate_with_no_situation_codes_is_covered_by_no_variant() -> None:
    candidates = {
        C1: [(P1, None)],
        C2: [(P1, [])],
        C3: [(P1, None), (P2, [])],
    }

    result = situation_coverage_by_variant(candidates, (BASELINE, RELAXED_SINGLE_PROCEDURE))

    by_variant = {row.variant: row for row in result}
    assert by_variant[RELAXED_SINGLE_PROCEDURE.name].accepted_candidates == 0
    assert by_variant[RELAXED_SINGLE_PROCEDURE.name].newly_covered_candidates == 0
