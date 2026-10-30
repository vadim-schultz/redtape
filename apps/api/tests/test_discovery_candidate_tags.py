"""Tag suggestions of a candidate: consensus of extracted mentions, replaced per axis by manual mentions (D18)."""

from __future__ import annotations

import uuid

from app.features.discovery.candidate_tags import accepted_codes, candidate_tag_suggestions
from app.features.discovery.tags import MANUAL_EXTRACTOR, TagSupport
from app.models.discovery import DiscoveryCandidateMention

P1, P2 = uuid.uuid4(), uuid.uuid4()


def _mention(
    procedure: uuid.UUID, extractor: str, domains: list[str] | None = None, situations: list[str] | None = None
) -> DiscoveryCandidateMention:
    return DiscoveryCandidateMention(
        catalogue_service_id=procedure, extractor=extractor, domain_codes=domains, situation_codes=situations
    )


def test_a_manual_mention_replaces_the_domain_consensus() -> None:
    mentions = [_mention(P1, "llm", ["housing"]), _mention(P2, "llm", ["housing"]), _mention(P1, "manual", ["work"])]

    suggestions = candidate_tag_suggestions(mentions)

    assert suggestions.domains == [TagSupport("work", procedures=1, share=1.0, accepted=True)]
    assert accepted_codes(suggestions.domains) == ["work"]


def test_the_override_is_per_axis() -> None:
    mentions = [_mention(P1, MANUAL_EXTRACTOR, ["work"]), _mention(P1, "llm", None, ["moving"])]

    suggestions = candidate_tag_suggestions(mentions)

    assert accepted_codes(suggestions.domains) == ["work"]
    assert suggestions.situations == [TagSupport("moving", procedures=1, share=1.0, accepted=False)]


def test_a_manual_mention_without_codes_leaves_the_consensus_in_force() -> None:
    mentions = [_mention(P1, "llm", ["housing"]), _mention(P2, "llm", ["housing"]), _mention(P1, "manual", [], None)]

    assert accepted_codes(candidate_tag_suggestions(mentions).domains) == ["housing"]
