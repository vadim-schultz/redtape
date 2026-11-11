"""The one i18n picker shared by locations, taxonomy, documents and candidates."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from app.shared.locale import ResolvedLocale, fallback_chain


def pick_i18n(
    values: Mapping[str, object] | None,
    locale: ResolvedLocale,
    *,
    fallback: Sequence[str] | None = None,
) -> str:
    """Resolve a JSONB i18n map.

    Order: :func:`~app.shared.locale.fallback_chain` of ``locale.code`` (German readers
    ``de, en``; others ``code, en, de``), then sorted ``locale.enabled``, then any
    non-blank value. An explicit ``fallback`` replaces everything after ``locale.code``
    in the first step; see ``features.suggestions.slugs.pick_title``, which needs
    en-first because its output feeds durable slugs and dedup keys.
    """
    if not values:
        return ""
    order = fallback_chain(locale.code) if fallback is None else (locale.code, *fallback)
    found = _first_non_blank(values, order) or _first_non_blank(values, sorted(locale.enabled))
    return found or _any_non_blank(values)


def _first_non_blank(values: Mapping[str, object], codes: Iterable[str]) -> str:
    """Return the first non-blank value stored under one of ``codes``, or ``""``."""
    for code in codes:
        if code in values and str(values[code]).strip():
            return str(values[code])
    return ""


def _any_non_blank(values: Mapping[str, object]) -> str:
    """Return the first non-blank, non-null value in ``values``, or ``""``."""
    for value in values.values():
        if value is not None and str(value).strip():
            return str(value)
    return ""
