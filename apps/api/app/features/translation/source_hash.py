"""The hash of a translation unit's German source; a stored translation whose hash differs is stale."""

from __future__ import annotations

import hashlib


def source_hash(title: str, description: str, *, recipe_version: str) -> str:
    """Return the SHA-256 hex digest of ``recipe_version``, ``title`` and ``description``, NUL-delimited.

    The delimiter keeps ``("ab", "c")`` and ``("a", "bc")`` apart; ``recipe_version`` is
    ``TRANSLATION_UNIT_RECIPE_VERSION``, so changing how the unit is built makes every translation stale.
    """
    return hashlib.sha256("\0".join((recipe_version, title, description)).encode()).hexdigest()
