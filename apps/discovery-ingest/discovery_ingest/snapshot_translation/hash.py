"""The source hash of a page: SHA-256 over its cleaned text and the cleaner version, the same for every locale."""

from __future__ import annotations

import hashlib
from typing import Final

from discovery_ingest.extract.clean import CLEAN_VERSION

SEPARATOR: Final = b"\x00"


def source_hash(text: str) -> str:
    """Return the hex SHA-256 of ``text``, a NUL byte and ``CLEAN_VERSION``.

    Raw HTML that differs only in nonces or timestamps has the same cleaned text, so it has the same hash.
    """
    return hashlib.sha256(text.encode("utf-8") + SEPARATOR + CLEAN_VERSION.encode("utf-8")).hexdigest()
