"""In-memory ``ObjectStore`` for tests."""

from __future__ import annotations

from urllib.parse import quote, urlencode

from app.shared.object_store.errors import ObjectNotFoundError
from app.shared.object_store.port import PRESIGN_TTL_SECONDS, content_disposition


class InMemoryObjectStore:
    """Dictionary-backed store whose presigned URLs are deterministic ``memory://`` strings."""

    def __init__(self) -> None:
        """Start empty."""
        self._objects: dict[str, tuple[bytes, str]] = {}

    def put(self, key: str, data: bytes, content_type: str) -> None:
        """Store ``data`` and its ``content_type`` under ``key``."""
        self._objects[key] = (data, content_type)

    def get(self, key: str) -> bytes:
        """Return the bytes at ``key`` or raise :class:`ObjectNotFoundError`."""
        if key not in self._objects:
            raise ObjectNotFoundError(key)
        return self._objects[key][0]

    def content_type(self, key: str) -> str:
        """Return the content type stored at ``key`` (test helper outside the port)."""
        if key not in self._objects:
            raise ObjectNotFoundError(key)
        return self._objects[key][1]

    def exists(self, key: str) -> bool:
        """Return whether ``key`` is stored."""
        return key in self._objects

    def delete(self, key: str) -> None:
        """Remove ``key`` if present."""
        self._objects.pop(key, None)

    def presigned_get_url(
        self, key: str, *, expires_in: int = PRESIGN_TTL_SECONDS, download_name: str | None = None
    ) -> str:
        """Return ``memory://<key>?expires_in=...`` with the same disposition override S3 would carry."""
        params = {"expires_in": str(expires_in)}
        if download_name is not None:
            params["response-content-disposition"] = content_disposition(download_name)
        return f"memory://{quote(key)}?{urlencode(params)}"
