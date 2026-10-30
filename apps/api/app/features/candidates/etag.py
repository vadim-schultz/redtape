"""Entity tags of content-addressed artifacts and the ``If-None-Match`` comparison."""

from __future__ import annotations


def etag_of(sha256: str) -> str:
    """Return the strong entity tag of an artifact: its sha256 in quotes."""
    return f'"{sha256}"'


def _opaque(tag: str) -> str:
    """Strip the weak marker; a weak match is enough for a conditional GET (RFC 9110, 13.1.2)."""
    return tag.strip().removeprefix("W/")


def etag_matches(if_none_match: str | None, etag: str) -> bool:
    """Return whether the ``If-None-Match`` header names ``etag`` or ``*``."""
    if if_none_match is None:
        return False
    tags = {_opaque(tag) for tag in if_none_match.split(",")}
    return "*" in tags or etag in tags
