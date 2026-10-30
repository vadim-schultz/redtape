"""Tag consensus over a candidate's mentions (extraction chapter E1, loop D)."""

from __future__ import annotations

import uuid

import pytest
from app.features.discovery.tags import MANUAL_EXTRACTOR, TagSupport, aggregate_tags, curated_codes

P1, P2, P3, P4, P5 = (uuid.uuid4() for _ in range(5))


def _by_code(result: list[TagSupport]) -> dict[str, TagSupport]:
    return {entry.code: entry for entry in result}


def test_aggregate_counts_distinct_procedures_not_mentions() -> None:
    mentions = [(P1, ["housing"]), (P1, ["housing"]), (P1, ["housing", "work"]), (P2, ["housing"])]

    result = _by_code(aggregate_tags(mentions))

    assert result["housing"] == TagSupport("housing", procedures=2, share=1.0, accepted=True)
    assert result["work"] == TagSupport("work", procedures=1, share=0.5, accepted=False)


def test_aggregate_accepts_a_code_at_exactly_two_procedures_and_fifty_percent() -> None:
    mentions = [(P1, ["a"]), (P2, ["a"]), (P3, ["b"]), (P4, ["b"])]

    result = _by_code(aggregate_tags(mentions))

    assert result["a"] == TagSupport("a", procedures=2, share=0.5, accepted=True)


def test_aggregate_does_not_accept_a_code_seen_on_one_procedure() -> None:
    result = aggregate_tags([(P1, ["housing"]), (P1, ["housing"])])

    assert result == [TagSupport("housing", procedures=1, share=1.0, accepted=False)]


def test_aggregate_does_not_accept_a_code_below_the_share() -> None:
    mentions = [(P1, ["a"]), (P2, ["a"]), (P3, ["b"]), (P4, ["b"]), (P5, ["b"])]

    result = _by_code(aggregate_tags(mentions))

    assert result["a"].accepted is False
    assert result["a"].share == pytest.approx(0.4)
    assert result["b"].accepted is True


def test_aggregate_ignores_mentions_without_codes_in_the_share() -> None:
    mentions = [(P1, ["a"]), (P2, ["a"]), (P3, None), (P4, [])]

    assert aggregate_tags(mentions) == [TagSupport("a", procedures=2, share=1.0, accepted=True)]
    assert aggregate_tags([(P3, None), (P4, [])]) == []


def test_aggregate_thresholds_are_parameters_and_the_result_is_ordered() -> None:
    mentions = [(P1, ["b", "a"]), (P2, ["a"])]

    result = aggregate_tags(mentions, min_procedures=3)

    assert [(e.code, e.procedures, e.accepted) for e in result] == [("a", 2, False), ("b", 1, False)]
    assert aggregate_tags(mentions, min_procedures=1, min_share=0.9)[1].accepted is False


def test_curated_codes_take_one_procedure_and_ignore_the_extracted_consensus() -> None:
    mentions = [(P1, "pvog_payload", ["housing"]), (P2, "pvog_payload", ["housing"]), (P3, MANUAL_EXTRACTOR, ["work"])]

    assert curated_codes(mentions) == [TagSupport("work", procedures=1, share=1.0, accepted=True)]


def test_curated_codes_union_the_manual_mentions_and_count_their_procedures() -> None:
    mentions = [(P1, MANUAL_EXTRACTOR, ["b", "a"]), (P2, MANUAL_EXTRACTOR, ["a"]), (P2, MANUAL_EXTRACTOR, ["a"])]

    assert curated_codes(mentions) == [
        TagSupport("a", procedures=2, share=1.0, accepted=True),
        TagSupport("b", procedures=1, share=1.0, accepted=True),
    ]


def test_curated_codes_are_empty_without_a_manual_mention_carrying_codes() -> None:
    mentions = [(P1, "llm", ["housing"]), (P2, MANUAL_EXTRACTOR, None), (P3, MANUAL_EXTRACTOR, [])]

    assert curated_codes(mentions) == []
    assert curated_codes([]) == []
