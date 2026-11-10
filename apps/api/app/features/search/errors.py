"""Domain errors of the search work queues; the machine router maps them to HTTP."""

from __future__ import annotations

from app.features.discovery.errors import DiscoveryError


class TaskNotOwnedError(DiscoveryError):
    """The task does not exist, is not claimed, or is claimed by another key."""

    def __init__(self) -> None:
        """Build the error with its fixed message."""
        super().__init__("Task is not claimed by this API key")


class InvalidTaskMoveError(Exception):
    """A task was asked to leave its status in a way the status table does not allow."""
