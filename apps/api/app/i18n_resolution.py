from __future__ import annotations

from collections.abc import Iterable, Mapping


def pick_i18n(
    values: Mapping[str, object] | None,
    *,
    locale: str,
    enabled: Iterable[str],
) -> str:
    """Resolve JSONB i18n map: requested → de → en → first enabled key → any value."""
    if not values:
        return ""
    enabled_set = set(enabled)
    for code in (locale, "de", "en"):
        if code in values and str(values[code]).strip():
            return str(values[code])
    for key in sorted(enabled_set):
        if key in values and str(values[key]).strip():
            return str(values[key])
    for _k, v in values.items():
        if v is not None and str(v).strip():
            return str(v)
    return ""
