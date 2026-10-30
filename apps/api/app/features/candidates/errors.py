"""Domain errors of the public candidate view; the discovery handlers map them to HTTP."""

from __future__ import annotations

from app.features.discovery.errors import DiscoveryNotFoundError


class CandidateScreenshotNotFoundError(DiscoveryNotFoundError):
    """The candidate has no screenshot, or its stored image is gone."""

    def __init__(self) -> None:
        """Build the error with its fixed message."""
        super().__init__("Candidate has no screenshot")
