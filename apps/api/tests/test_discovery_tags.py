"""Tag confidence scoring vocabulary (situation-tag-hierarchy chapter 1): the LLM-evidence curve and
noisy-OR combination that replaced the binary accept/reject gate and its per-axis thresholds.
"""

from __future__ import annotations

import pytest
from app.features.discovery.tags import (
    LLM_SCORE_CEILING,
    MIN_SUGGESTED_SCORE,
    TagAxis,
    llm_evidence_score,
    noisy_or,
)
from app.models.discovery import DiscoveryCandidateMention as Mention


def test_each_axis_points_at_its_own_mention_column() -> None:
    assert TagAxis.DOMAIN.column is Mention.domain_codes
    assert TagAxis.SITUATION.column is Mention.situation_codes


def test_each_axis_points_at_its_own_direct_confidence_column() -> None:
    assert TagAxis.DOMAIN.confidence_column is Mention.direct_domain_confidence
    assert TagAxis.SITUATION.confidence_column is Mention.direct_situation_confidence


def test_llm_evidence_score_is_zero_without_any_procedure() -> None:
    assert llm_evidence_score(0, 0.0) == 0.0


def test_llm_evidence_score_is_monotonic_in_procedures_at_a_fixed_share() -> None:
    one = llm_evidence_score(1, 1.0)
    two = llm_evidence_score(2, 1.0)
    three = llm_evidence_score(3, 1.0)

    assert one < two <= three


def test_llm_evidence_score_scales_with_share() -> None:
    full = llm_evidence_score(1, 1.0)
    half = llm_evidence_score(1, 0.5)

    assert half == pytest.approx(full / 2)


def test_llm_evidence_score_saturates_at_the_ceiling() -> None:
    assert llm_evidence_score(50, 1.0) == pytest.approx(LLM_SCORE_CEILING)


def test_noisy_or_of_no_evidence_is_zero() -> None:
    assert noisy_or([]) == 0.0


def test_noisy_or_of_a_single_certain_source_is_certain() -> None:
    assert noisy_or([1.0]) == 1.0


def test_noisy_or_combines_two_independent_sources_above_either_alone() -> None:
    combined = noisy_or([0.5, 0.5])

    assert combined == pytest.approx(0.75)


def test_noisy_or_treats_a_zero_term_as_the_identity() -> None:
    assert noisy_or([0.0, 0.6]) == pytest.approx(0.6)


def test_min_suggested_score_is_a_small_noise_floor_not_a_precision_bar() -> None:
    assert 0 < MIN_SUGGESTED_SCORE < 0.5
