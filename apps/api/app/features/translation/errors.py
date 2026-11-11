"""Domain errors of reading a stored translation; the discovery handlers map them to HTTP."""

from __future__ import annotations

from app.features.discovery.errors import DiscoveryNotFoundError


class TranslationNotFoundError(DiscoveryNotFoundError):
    """The candidate has no stored translation into the requested locale, or its stored text cannot be read."""

    def __init__(self) -> None:
        """Build the error with its fixed message."""
        super().__init__("Translation not found")
