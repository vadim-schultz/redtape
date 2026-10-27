"""Which artifacts are accepted: content types, size limits and the content-addressed key."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.features.discovery.errors import ArtifactTooLargeError, UnsupportedArtifactTypeError
from app.models.discovery import DiscoveryArtifactKind

MEGABYTE = 1024 * 1024
KEEP_LATEST_SNAPSHOTS = 2


class ByteSource(Protocol):
    """Anything that reads a bounded number of bytes, such as an uploaded file."""

    def read(self, size: int, /) -> bytes:
        """Return at most ``size`` bytes."""
        ...


@dataclass(frozen=True, slots=True)
class ArtifactLimit:
    """Allowed content types (mapped to a key extension) and the byte ceiling for one artifact kind."""

    extensions: Mapping[str, str]
    max_bytes: int


ARTIFACT_LIMITS: Mapping[DiscoveryArtifactKind, ArtifactLimit] = {
    DiscoveryArtifactKind.HTML_SNAPSHOT: ArtifactLimit({"text/html": "html"}, 4 * MEGABYTE),
    DiscoveryArtifactKind.SCREENSHOT: ArtifactLimit({"image/png": "png", "image/jpeg": "jpg"}, 8 * MEGABYTE),
}
MAX_ARTIFACT_BYTES = max(limit.max_bytes for limit in ARTIFACT_LIMITS.values())


def media_type(content_type: str | None) -> str:
    """Return ``content_type`` without parameters, lower-cased (``text/html; charset=utf-8`` -> ``text/html``)."""
    return (content_type or "").split(";", 1)[0].strip().lower()


def read_capped(file: ByteSource) -> bytes:
    """Read at most one byte more than the largest limit, so an oversize body never fills memory."""
    return file.read(MAX_ARTIFACT_BYTES + 1)


def extension_for(kind: DiscoveryArtifactKind, content_type: str, size: int) -> str:
    """Return the key extension for an acceptable artifact; raise 415/413 errors otherwise."""
    limit = ARTIFACT_LIMITS[kind]
    if content_type not in limit.extensions:
        raise UnsupportedArtifactTypeError(f"{kind.value} does not accept content type {content_type or 'none'}")
    if size > limit.max_bytes:
        raise ArtifactTooLargeError(f"{kind.value} is limited to {limit.max_bytes} bytes")
    return limit.extensions[content_type]


def storage_key(catalogue_service_id: UUID, kind: DiscoveryArtifactKind, sha256: str, extension: str) -> str:
    """Return the content-addressed object key ``discovery/{catalogue}/{kind}/{sha256}.{ext}``."""
    return f"discovery/{catalogue_service_id}/{kind.value}/{sha256}.{extension}"
