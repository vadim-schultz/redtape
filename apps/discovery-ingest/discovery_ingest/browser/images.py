"""Recognise the image formats Cloudflare returns by their first bytes."""

from __future__ import annotations

_MAGIC = ((b"\xff\xd8\xff", "jpeg"), (b"\x89PNG", "png"), (b"RIFF", "webp"))
CONTENT_TYPES = {"jpeg": "image/jpeg", "png": "image/png"}


def image_kind(data: bytes) -> str:
    """Return ``jpeg``, ``png``, ``webp`` or ``bytes`` (unrecognised) for ``data``."""
    return next((name for magic, name in _MAGIC if data.startswith(magic)), "bytes")
