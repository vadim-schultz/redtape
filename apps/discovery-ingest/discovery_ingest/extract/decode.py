"""Decode stored page bytes to text: header charset, then meta charset, then UTF-8 with replacement."""

from __future__ import annotations

import re
from collections.abc import Iterator

_HEADER_CHARSET = re.compile(r"charset\s*=\s*[\"']?([\w.:-]+)", re.IGNORECASE)
_META_CHARSET = re.compile(rb"<meta[^>]+charset\s*=\s*[\"']?([\w.:-]+)", re.IGNORECASE)
_SNIFF_BYTES = 4096


def decode_html(body: bytes, content_type: str | None) -> str:
    """Return ``body`` as text without NUL characters; this is the one place page bytes become text.

    The ``Content-Type`` charset wins, then a ``<meta charset>`` in the first 4 KB. A charset that is unknown or cannot
    decode the bytes is skipped, and the last resort is UTF-8 with replacement characters, so this never raises.
    """
    for label in _declared_charsets(body, content_type):
        text = _decode_strictly(body, label)
        if text is not None:
            return text.replace("\x00", "")
    return body.decode("utf-8", errors="replace").replace("\x00", "")


def _declared_charsets(body: bytes, content_type: str | None) -> Iterator[str]:
    header = _HEADER_CHARSET.search(content_type or "")
    if header:
        yield header.group(1)
    meta = _META_CHARSET.search(body[:_SNIFF_BYTES])
    if meta:
        yield meta.group(1).decode("ascii", errors="ignore")


def _decode_strictly(body: bytes, label: str) -> str | None:
    try:
        return body.decode(label)
    except (LookupError, UnicodeDecodeError):
        return None
