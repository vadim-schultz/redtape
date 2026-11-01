"""Pure helpers over a candidate's per-code ``TagSupport`` list (chapter 2, tag confidence tier)."""

from __future__ import annotations

from app.features.discovery.candidate_tags import accepted_codes, accepted_supports
from app.features.discovery.tags import TagSupport


def test_accepted_supports_filters_without_collapsing_to_bare_codes() -> None:
    supports = [
        TagSupport("a", procedures=2, share=1.0, accepted=True),
        TagSupport("b", procedures=1, share=0.5, accepted=False),
    ]

    assert accepted_supports(supports) == [supports[0]]


def test_accepted_supports_and_accepted_codes_agree_on_which_codes_clear_the_bar() -> None:
    supports = [
        TagSupport("a", procedures=2, share=1.0, accepted=True),
        TagSupport("b", procedures=1, share=0.5, accepted=False),
    ]

    assert [support.code for support in accepted_supports(supports)] == accepted_codes(supports)
