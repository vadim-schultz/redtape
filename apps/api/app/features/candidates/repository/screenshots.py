"""The screenshots of the procedures that mention a candidate: the newest, the history, and one capture by id (D7, D11)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, select

from app.features.discovery.repository.base import SessionRepository
from app.models.discovery import DiscoveryArtifact, DiscoveryArtifactKind
from app.models.discovery import DiscoveryCandidateMention as Mention


def _screenshots_of(candidate_id: UUID) -> Select[tuple[DiscoveryArtifact]]:
    """Return the screenshots of any procedure that mentions ``candidate_id``, newest first (``fetched_at``, then id)."""
    procedures = select(Mention.catalogue_service_id).where(Mention.candidate_id == candidate_id)
    return (
        select(DiscoveryArtifact)
        .where(
            DiscoveryArtifact.kind == DiscoveryArtifactKind.SCREENSHOT,
            DiscoveryArtifact.catalogue_service_id.in_(procedures),
        )
        .order_by(DiscoveryArtifact.fetched_at.desc(), DiscoveryArtifact.id.desc())
    )


class ScreenshotRepository(SessionRepository):
    """Look up the screenshot rows of a candidate."""

    def newest_screenshot(self, candidate_id: UUID) -> DiscoveryArtifact | None:
        """Return the screenshot with the latest ``fetched_at`` (then id) of any mentioning procedure."""
        rows = self.list_screenshots(candidate_id, limit=1)
        return rows[0] if rows else None

    def list_screenshots(self, candidate_id: UUID, limit: int) -> list[DiscoveryArtifact]:
        """Return up to ``limit`` screenshots of any mentioning procedure, newest first."""
        return list(self._session.scalars(_screenshots_of(candidate_id).limit(limit)))

    def screenshot_of_candidate(self, candidate_id: UUID, artifact_id: UUID) -> DiscoveryArtifact | None:
        """Return the screenshot ``artifact_id`` when a procedure that mentions ``candidate_id`` holds it, else ``None``."""
        return self._session.scalar(_screenshots_of(candidate_id).where(DiscoveryArtifact.id == artifact_id))
