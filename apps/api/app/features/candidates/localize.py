"""Resolve stored i18n maps for the request locale."""

from __future__ import annotations

from app.i18n_resolution import pick_i18n
from app.shared.locale import ResolvedLocale


def localized(values: dict[str, str] | None, locale: ResolvedLocale) -> str:
    """Return the text for the requested locale, else German, English, or any stored text."""
    return pick_i18n(values, locale=locale.code, enabled=locale.enabled)
