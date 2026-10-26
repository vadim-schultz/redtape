"""Decorator that reports every billable operation to an injected meter before touching the store."""

from __future__ import annotations

from app.shared.object_store.port import PRESIGN_TTL_SECONDS, ObjectStore, ObjectStoreMeter


class MeteredObjectStore:
    """Call ``meter`` first so a raising meter (a cap) stops the operation untouched."""

    def __init__(self, inner: ObjectStore, meter: ObjectStoreMeter) -> None:
        """Wrap ``inner`` and report to ``meter``."""
        self._inner = inner
        self._meter = meter

    def put(self, key: str, data: bytes, content_type: str) -> None:
        """Count one Class A operation, then upload."""
        self._meter("class_a", 1)
        self._inner.put(key, data, content_type)

    def get(self, key: str) -> bytes:
        """Count one Class B operation, then download."""
        self._meter("class_b", 1)
        return self._inner.get(key)

    def exists(self, key: str) -> bool:
        """Count one Class B operation, then HEAD."""
        self._meter("class_b", 1)
        return self._inner.exists(key)

    def delete(self, key: str) -> None:
        """Count one Class A operation, then delete."""
        self._meter("class_a", 1)
        self._inner.delete(key)

    def presigned_get_url(
        self, key: str, *, expires_in: int = PRESIGN_TTL_SECONDS, download_name: str | None = None
    ) -> str:
        """Presign without metering: signing is local and costs nothing."""
        return self._inner.presigned_get_url(key, expires_in=expires_in, download_name=download_name)
