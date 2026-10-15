"""Canonical URL normalization for discovery staging entities."""

from __future__ import annotations

from app.schema.suggestion.payload import validate_url
from app.url_normalization import normalize_url


def normalize_canonical_url(url: str) -> str:
    """Validate ``url`` and return the suggestion-style normalized form."""
    validate_url(url, field="canonical_url")
    return normalize_url(url)
