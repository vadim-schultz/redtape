"""The ``ObjectStore`` port: the only storage surface the rest of the application may import."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Literal, Protocol

PRESIGN_TTL_SECONDS = 300
"""Lifetime of a presigned GET URL; a constant, not a setting."""

OperationClass = Literal["class_a", "class_b"]
"""R2 billing classes: A is write, B is read or head. Presigning is local and free."""

ObjectStoreMeter = Callable[[OperationClass, int], None]
"""Counts ``n`` operations of one class and raises :class:`ObjectStoreQuotaError` over a cap."""

_UNSAFE_FILENAME = re.compile(r'[\x00-\x1f\x7f"\\/]')


def content_disposition(download_name: str) -> str:
    """Return an ``attachment`` header value for ``download_name`` with quotes and separators removed."""
    return f'attachment; filename="{_UNSAFE_FILENAME.sub("", download_name)}"'


def noop_meter(kind: OperationClass, n: int) -> None:
    """Accept and ignore every operation; the default until the ledger-backed meter exists."""


class ObjectStore(Protocol):
    """Key-agnostic blob storage. There is deliberately no ``list`` (a Class A operation)."""

    def put(self, key: str, data: bytes, content_type: str) -> None:
        """Store ``data`` under ``key``, replacing any existing object."""
        ...

    def get(self, key: str) -> bytes:
        """Return the bytes at ``key`` or raise :class:`ObjectNotFoundError`."""
        ...

    def exists(self, key: str) -> bool:
        """Return whether ``key`` exists (HEAD, Class B); callers prefer the database sha256 key."""
        ...

    def delete(self, key: str) -> None:
        """Remove ``key``; deleting a missing key is a no-op."""
        ...

    def presigned_get_url(
        self, key: str, *, expires_in: int = PRESIGN_TTL_SECONDS, download_name: str | None = None
    ) -> str:
        """Mint a GET URL valid for ``expires_in`` seconds; ``download_name`` forces a download."""
        ...
