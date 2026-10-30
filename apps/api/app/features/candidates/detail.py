"""Assemble the detail of a candidate from its card, edges, mentions and newest screenshot."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.features.candidates.card_builder import CardContext
from app.features.candidates.links import merged_neighbours, sources_of
from app.features.discovery.repository import EdgeRow
from app.features.discovery.repository.candidate_listing import CandidateMentionRow
from app.models.discovery import DiscoveryArtifact
from app.schema.candidate import CandidateCard, CandidateDetail, CandidateScreenshot

SCREENSHOT_PATH = "/api/v1/candidates/{candidate_id}/screenshot"


@dataclass(frozen=True, slots=True)
class Evidence:
    """The rows behind a detail: its edges, its mentions and the newest screenshot, if any."""

    edges: Sequence[EdgeRow]
    mentions: Sequence[CandidateMentionRow]
    screenshot: DiscoveryArtifact | None


def screenshot_ref(card: CandidateCard, artifact: DiscoveryArtifact | None) -> CandidateScreenshot | None:
    """Return the relative proxy path and fetch time of ``artifact``; never a presigned URL (D3)."""
    if artifact is None:
        return None
    return CandidateScreenshot(url=SCREENSHOT_PATH.format(candidate_id=card.id), fetched_at=artifact.fetched_at)


def detail_of(card: CandidateCard, evidence: Evidence, context: CardContext) -> CandidateDetail:
    """Extend ``card`` with ingress (edges it is the parent of), egress, sources and the screenshot reference."""
    into = [row for row in evidence.edges if row.parent.id == card.id]
    out = [row for row in evidence.edges if row.required.id == card.id]
    ingress = merged_neighbours(into, lambda row: row.required, context)
    egress = merged_neighbours(out, lambda row: row.parent, context)
    return CandidateDetail(
        **card.model_dump(),
        ingress=ingress.items,
        ingress_truncated=ingress.truncated,
        egress=egress.items,
        egress_truncated=egress.truncated,
        sources=sources_of(evidence.mentions, context.locale),
        screenshot=screenshot_ref(card, evidence.screenshot),
    )
