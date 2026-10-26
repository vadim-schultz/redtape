"""Errors raised by object store adapters; routes and workers map them to HTTP and release."""

from __future__ import annotations


class ObjectStoreError(Exception):
    """Base class for every object store failure."""


class ObjectNotFoundError(ObjectStoreError):
    """The requested key does not exist in the store."""

    def __init__(self, key: str) -> None:
        """Build the error naming the missing ``key``."""
        super().__init__(f"Object not found: {key}")


class ObjectStoreUnavailableError(ObjectStoreError):
    """The store is not configured, not reachable, or refused the call.

    Routes answer 503; workers release the task and stop with ``storage_unavailable``.
    """


class ObjectStoreQuotaError(ObjectStoreUnavailableError):
    """A metering cap stopped the call before the store was touched.

    Mapped exactly like :class:`ObjectStoreUnavailableError`, which it extends on purpose.
    """
