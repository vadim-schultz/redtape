"""Domain errors raised by discovery services and repositories; routers map them to HTTP."""

from __future__ import annotations

from uuid import UUID


class DiscoveryError(Exception):
    """Base class for every discovery domain failure."""


class DiscoveryNotFoundError(DiscoveryError):
    """A referenced discovery record does not exist."""


class CatalogueNotFoundError(DiscoveryNotFoundError):
    """The catalogue service does not exist."""

    def __init__(self) -> None:
        """Build the error with its fixed message."""
        super().__init__("Catalogue service not found")


class DiscoveryTaskNotFoundError(DiscoveryNotFoundError):
    """The discovery task does not exist."""

    def __init__(self) -> None:
        """Build the error with its fixed message."""
        super().__init__("Discovery task not found")


class DiscoveryEntityNotFoundError(DiscoveryNotFoundError):
    """The discovery entity does not exist."""

    def __init__(self) -> None:
        """Build the error with its fixed message."""
        super().__init__("Discovery entity not found")


class InvalidDiscoveryInputError(DiscoveryError):
    """Submitted data is well-formed but unacceptable."""


class UnknownJurisdictionError(InvalidDiscoveryInputError):
    """A catalogue item references a jurisdiction that does not exist."""

    def __init__(self, jurisdiction_id: UUID) -> None:
        """Build the error naming the offending ``jurisdiction_id``."""
        super().__init__(f"Unknown jurisdiction_id: {jurisdiction_id}")
