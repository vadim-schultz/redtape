"""The one i18n picker shared by locations, taxonomy, documents and candidates."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.shared.locale import FALLBACK_ORDER, ResolvedLocale


def pick_i18n(
    values: Mapping[str, object] | None,
    locale: ResolvedLocale,
    *,
    fallback: Sequence[str] = FALLBACK_ORDER,
) -> str:
    """Resolve a JSONB i18n map.

    Order: ``locale.code``, then ``fallback`` (de, en by default), then sorted
    ``locale.enabled``, then any non-blank value. ``fallback`` lets a caller pick a
    different order; see ``features.suggestions.slugs.pick_title``, which needs
    en-first because its output feeds durable slugs and dedup keys.
    """
    if not values:
        return ""
    for code in (locale.code, *fallback):
        if code in values and str(values[code]).strip():
            return str(values[code])
    for key in sorted(locale.enabled):
        if key in values and str(values[key]).strip():
            return str(values[key])
    for value in values.values():
        if value is not None and str(value).strip():
            return str(value)
    return ""
