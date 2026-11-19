"""Assemble the detail of a candidate from its card, edges, mentions and screenshot history."""

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
CAPTURE_PATH = "/api/v1/candidates/{candidate_id}/screenshots/{artifact_id}"


@dataclass(frozen=True, slots=True)
class Evidence:
    """The rows behind a detail: its edges, its mentions and its screenshots, newest first."""

    edges: Sequence[EdgeRow]
    mentions: Sequence[CandidateMentionRow]
    screenshots: Sequence[DiscoveryArtifact]


def capture_ref(card: CandidateCard, artifact: DiscoveryArtifact) -> CandidateScreenshot:
    """Return the relative proxy path of one capture and when it was fetched; never a presigned URL (D3)."""
    url = CAPTURE_PATH.format(candidate_id=card.id, artifact_id=artifact.id)
    return CandidateScreenshot(url=url, fetched_at=artifact.fetched_at)


def screenshot_fields(
    card: CandidateCard, artifacts: Sequence[DiscoveryArtifact]
) -> tuple[CandidateScreenshot | None, list[CandidateScreenshot]]:
    """Return the newest capture on the legacy route (``screenshot``, D13) and the whole history (``screenshots``)."""
    if not artifacts:
        return None, []
    newest = CandidateScreenshot(url=SCREENSHOT_PATH.format(candidate_id=card.id), fetched_at=artifacts[0].fetched_at)
    return newest, [capture_ref(card, artifact) for artifact in artifacts]


def detail_of(card: CandidateCard, evidence: Evidence, context: CardContext) -> CandidateDetail:
    """Extend ``card`` with ingress (edges it is the parent of), egress, sources and the screenshot fields."""
    into = [row for row in evidence.edges if row.parent.id == card.id]
    out = [row for row in evidence.edges if row.required.id == card.id]
    ingress = merged_neighbours(into, lambda row: row.required, context)
    egress = merged_neighbours(out, lambda row: row.parent, context)
    screenshot, screenshots = screenshot_fields(card, evidence.screenshots)
    return CandidateDetail(
        **card.model_dump(),
        ingress=ingress.items,
        ingress_truncated=ingress.truncated,
        egress=egress.items,
        egress_truncated=egress.truncated,
        sources=sources_of(evidence.mentions, context.locale),
        screenshot=screenshot,
        screenshots=screenshots,
    )
