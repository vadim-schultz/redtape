"""Content hash of a search text; the recipe version is part of the input."""

from __future__ import annotations

import hashlib
from typing import Final

RECIPE_VERSION: Final = "v1"
"""Version of the canonical text recipe; bumping it changes every hash, so every text is embedded again."""


def content_hash(text: str) -> str:
    """Return the SHA-256 hex digest of the recipe version, a newline and ``text``."""
    return hashlib.sha256(f"{RECIPE_VERSION}\n{text}".encode()).hexdigest()
