"""Per-engine maps from our locale codes to the provider's; a map must cover every target locale."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Final

DEFAULT_TARGET_LOCALES: Final = ("en", "tr", "ru", "uk", "pl", "ro")
"""The six locales document text is translated into. ``TRANSLATION_TARGET_LOCALES`` on the API defaults to the same list;
``tests/test_translation_locales_parity.py`` holds the two equal."""

_MAPS: dict[str, Mapping[str, str]] = {}


class UnmappedLocaleError(LookupError):
    """The engine has no provider code for a locale it was asked to translate into."""


def register_locale_map(engine: str, mapping: Mapping[str, str]) -> None:
    """Register ``mapping`` (our code to the provider's) for ``engine``, replacing an earlier one."""
    _MAPS[engine] = dict(mapping)


def unregister_locale_map(engine: str) -> None:
    """Remove the map of ``engine`` (tests that register a throwaway engine)."""
    _MAPS.pop(engine, None)


def provider_code(engine: str, locale: str) -> str:
    """Return the provider's code for ``locale`` on ``engine``, or raise :class:`UnmappedLocaleError`."""
    try:
        return _MAPS[engine][locale]
    except KeyError:
        raise UnmappedLocaleError(f"engine {engine!r} has no provider code for locale {locale!r}") from None


def require_coverage(engine: str, locales: Iterable[str]) -> None:
    """Raise :class:`UnmappedLocaleError` naming every locale of ``locales`` that ``engine`` cannot map."""
    missing = [locale for locale in locales if locale not in _MAPS.get(engine, {})]
    if missing:
        raise UnmappedLocaleError(f"engine {engine!r} has no provider code for locales {missing}")
