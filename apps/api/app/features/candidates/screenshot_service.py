"""Serve the newest screenshot of a candidate: found by the database, read from the metered object store."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.features.candidates.errors import CandidateScreenshotNotFoundError
from app.features.candidates.etag import etag_matches, etag_of
from app.features.candidates.repository import PublicCandidateRepository
from app.features.discovery.errors import CandidateNotFoundError
from app.models.discovery import DiscoveryArtifact
from app.shared.object_store import ObjectNotFoundError, ObjectStore
from app.shared.object_store.provider import require_store

CACHE_CONTROL = "public, max-age=31536000, immutable"


@dataclass(frozen=True, slots=True)
class ScreenshotReply:
    """What to answer: the entity tag, the content type, and the bytes (``None`` when the client copy is current)."""

    etag: str
    content_type: str
    data: bytes | None


class ScreenshotService:
    """Look up a candidate's screenshot and read its bytes at most once per changed image."""

    def __init__(self, repository: PublicCandidateRepository, store: ObjectStore | None) -> None:
        """Bind the service to ``repository`` and the metered, optional ``store``."""
        self._repo = repository
        self._store = store

    def serve(self, candidate_id: UUID, if_none_match: str | None) -> ScreenshotReply:
        """Return the screenshot reply; the store is not touched when ``if_none_match`` names the current image."""
        artifact = self._require_screenshot(candidate_id)
        etag = etag_of(artifact.sha256)
        if etag_matches(if_none_match, etag):
            return ScreenshotReply(etag, artifact.content_type, None)
        return ScreenshotReply(etag, artifact.content_type, self._read(artifact))

    def _require_screenshot(self, candidate_id: UUID) -> DiscoveryArtifact:
        if self._repo.get_candidate(candidate_id) is None:
            raise CandidateNotFoundError()
        artifact = self._repo.newest_screenshot(candidate_id)
        if artifact is None:
            raise CandidateScreenshotNotFoundError()
        return artifact

    def _read(self, artifact: DiscoveryArtifact) -> bytes:
        store = require_store(self._store)
        try:
            return store.get(artifact.storage_key)
        except ObjectNotFoundError as err:
            raise CandidateScreenshotNotFoundError() from err
