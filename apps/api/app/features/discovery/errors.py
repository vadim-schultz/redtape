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


class DiscoveryRunNotFoundError(DiscoveryNotFoundError):
    """The discovery run does not exist."""

    def __init__(self) -> None:
        """Build the error with its fixed message."""
        super().__init__("Discovery run not found")


class CandidateNotFoundError(DiscoveryNotFoundError):
    """The document candidate does not exist."""

    def __init__(self) -> None:
        """Build the error with its fixed message."""
        super().__init__("Document candidate not found")


class DiscoveryEntityNotFoundError(DiscoveryNotFoundError):
    """The discovery entity does not exist."""

    def __init__(self) -> None:
        """Build the error with its fixed message."""
        super().__init__("Discovery entity not found")


class ArtifactNotFoundError(DiscoveryNotFoundError):
    """The discovery artifact does not exist."""

    def __init__(self) -> None:
        """Build the error with its fixed message."""
        super().__init__("Discovery artifact not found")


class InvalidDiscoveryInputError(DiscoveryError):
    """Submitted data is well-formed but unacceptable."""


class UnknownJurisdictionError(InvalidDiscoveryInputError):
    """A catalogue item references a jurisdiction that does not exist."""

    def __init__(self, jurisdiction_id: UUID) -> None:
        """Build the error naming the offending ``jurisdiction_id``."""
        super().__init__(f"Unknown jurisdiction_id: {jurisdiction_id}")


class RunAlreadyFinishedError(InvalidDiscoveryInputError):
    """A run that already finished cannot be finished again."""

    def __init__(self) -> None:
        """Build the error with its fixed message."""
        super().__init__("Discovery run already finished")


class UnsupportedArtifactTypeError(DiscoveryError):
    """The artifact's content type is not allowed for its kind."""


class ArtifactTooLargeError(DiscoveryError):
    """The artifact is larger than its kind allows."""


class StorageCapExceededError(DiscoveryError):
    """Storing the artifact would take the stored bytes past ``object_store_max_bytes``."""


class TaskNotClaimedError(DiscoveryError):
    """Only a claimed task can be released."""

    def __init__(self) -> None:
        """Build the error with its fixed message."""
        super().__init__("Only a claimed task can be released")
