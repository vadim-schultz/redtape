"""Shared URL normalization, used by documents and suggestions for duplicate detection (D4)."""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

MAX_URL_LENGTH = 500
_TRACKING_PREFIXES = ("utm_",)
_TRACKING_EXACT = {"fbclid", "gclid"}


def _strip_tracking(query: str) -> str:
    pairs = parse_qsl(query, keep_blank_values=True)
    kept = [(k, v) for k, v in pairs if not k.startswith(_TRACKING_PREFIXES) and k not in _TRACKING_EXACT]
    return urlencode(kept)


def _sort_query(query: str) -> str:
    return urlencode(sorted(parse_qsl(query, keep_blank_values=True)))


def _trim_path(path: str) -> str:
    return path[:-1] if path.endswith("/") and path != "/" else path


def normalize_url(url: str) -> str:
    """Lower-case scheme/host, drop fragment and tracking params, sort query, trim trailing slash."""
    parts = urlsplit(url)
    query = _sort_query(_strip_tracking(parts.query))
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), _trim_path(parts.path), query, ""))


def validate_url(value: str, *, field: str = "official_url") -> str:
    """Reject URLs that exceed the length limit, are not http(s), or lack a host; return the value unchanged."""
    if len(value) > MAX_URL_LENGTH:
        raise ValueError(f"{field} exceeds {MAX_URL_LENGTH} characters")
    parsed = urlsplit(value)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"{field} must use http or https")
    if not parsed.netloc:
        raise ValueError(f"{field} must include a host")
    return value
