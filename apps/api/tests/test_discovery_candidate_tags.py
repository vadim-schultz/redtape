"""Pure helpers over a candidate's per-code ``TagSupport`` list (situation-tag-hierarchy chapter 1)."""

from __future__ import annotations

from app.features.discovery.candidate_tags import usable_codes, usable_supports
from app.features.discovery.tags import MIN_SUGGESTED_SCORE, TagSupport


def test_usable_supports_filters_without_collapsing_to_bare_codes() -> None:
    supports = [
        TagSupport("a", procedures=2, share=1.0, score=0.9),
        TagSupport("b", procedures=1, share=0.5, score=0.0),
    ]

    assert usable_supports(supports) == [supports[0]]


def test_usable_supports_and_usable_codes_agree_on_which_codes_clear_the_floor() -> None:
    supports = [
        TagSupport("a", procedures=2, share=1.0, score=0.9),
        TagSupport("b", procedures=1, share=0.5, score=0.0),
    ]

    assert [support.code for support in usable_supports(supports)] == usable_codes(supports)


def test_a_score_exactly_at_the_floor_is_usable() -> None:
    supports = [TagSupport("a", procedures=1, share=1.0, score=MIN_SUGGESTED_SCORE)]

    assert usable_codes(supports) == ["a"]


def test_a_score_just_below_the_floor_is_not_usable() -> None:
    supports = [TagSupport("a", procedures=1, share=1.0, score=MIN_SUGGESTED_SCORE - 0.001)]

    assert usable_codes(supports) == []
