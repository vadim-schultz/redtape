"""Resolve the request locale from `?locale=`, `Accept-Language`, or the de-then-en fallback."""

from __future__ import annotations

import re
from collections.abc import Iterable

from app.shared.locale import DEFAULT_ENABLED_LOCALES, FALLBACK_ORDER

_ACCEPT_LANG_PART = re.compile(r"^\s*(?P<tag>[a-zA-Z]{1,8}(?:-[a-zA-Z0-9]{1,8})*)(?:\s*;\s*q=(?P<q>[0-9.]+))?\s*$")


def parse_accept_language(header: str | None, enabled: set[str]) -> str | None:
    """Return best matching locale code from Accept-Language, or None."""
    if not header:
        return None
    preferences: list[tuple[float, str]] = []
    for raw in header.split(","):
        m = _ACCEPT_LANG_PART.match(raw)
        if not m:
            continue
        tag = m.group("tag")
        q_raw = m.group("q")
        q = float(q_raw) if q_raw is not None else 1.0
        primary = tag.split("-", 1)[0].lower()
        if len(primary) == 2 and primary in enabled:
            preferences.append((q, primary))
    if not preferences:
        return None
    preferences.sort(key=lambda item: item[0], reverse=True)
    return preferences[0][1]


def normalize_locale_tag(value: str | None) -> str | None:
    """Return the lower-cased two-letter primary subtag of `value`, or `None` when it has none."""
    if not value:
        return None
    primary = value.strip().split("-", 1)[0].lower()
    if len(primary) == 2 and primary.isalpha():
        return primary
    return None


def resolve_locale(
    *,
    query_locale: str | None,
    accept_language: str | None,
    enabled: Iterable[str],
) -> str:
    """Resolve locale: optional `?locale=` override, then Accept-Language, else de → en.

    Fallback chain when the requested tag is missing or not enabled:
    **requested → de → en → first enabled** (see roadmap Wave 0 / backend-api docs).
    """
    enabled_set = set(enabled)
    if not enabled_set:
        enabled_set = set(DEFAULT_ENABLED_LOCALES)

    requested = normalize_locale_tag(query_locale) or parse_accept_language(accept_language, enabled_set)

    if requested and requested in enabled_set:
        return requested

    for fallback in FALLBACK_ORDER:
        if fallback in enabled_set:
            return fallback

    return sorted(enabled_set)[0]
