"""Deduplication key of a document candidate (decision D7)."""

from __future__ import annotations

from app.features.discovery.errors import InvalidDiscoveryInputError
from app.features.suggestions.slugs import pick_title, slugify


def candidate_key(title_i18n: dict[str, str]) -> str:
    """Return the promotion slug of ``title_i18n``, or raise if the title has no usable characters."""
    try:
        return slugify(pick_title(title_i18n))
    except ValueError as err:
        raise InvalidDiscoveryInputError("Candidate title has no usable characters") from err
