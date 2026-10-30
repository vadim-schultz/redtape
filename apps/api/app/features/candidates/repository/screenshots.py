"""The newest screenshot among the procedures that mention a candidate (D7)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.features.discovery.repository.base import SessionRepository
from app.models.discovery import DiscoveryArtifact, DiscoveryArtifactKind
from app.models.discovery import DiscoveryCandidateMention as Mention


class ScreenshotRepository(SessionRepository):
    """Look up the artifact row behind a candidate's screenshot."""

    def newest_screenshot(self, candidate_id: UUID) -> DiscoveryArtifact | None:
        """Return the screenshot with the latest ``fetched_at`` (then id) of any mentioning procedure."""
        procedures = select(Mention.catalogue_service_id).where(Mention.candidate_id == candidate_id)
        stmt = (
            select(DiscoveryArtifact)
            .where(
                DiscoveryArtifact.kind == DiscoveryArtifactKind.SCREENSHOT,
                DiscoveryArtifact.catalogue_service_id.in_(procedures),
            )
            .order_by(DiscoveryArtifact.fetched_at.desc(), DiscoveryArtifact.id.desc())
            .limit(1)
        )
        return self._session.scalar(stmt)
