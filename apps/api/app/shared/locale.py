"""Request locale and the set of enabled locale codes, resolved once per request."""

from __future__ import annotations

from dataclasses import dataclass

from litestar import Request

DEFAULT_LOCALE = "de"


@dataclass(frozen=True, slots=True)
class LocaleSpec:
    """One supported interface locale; ``enabled_by_default`` seeds a new ``supported_locale`` row."""

    code: str
    name_native: str
    name_english: str
    flag_emoji: str
    enabled_by_default: bool = False


SUPPORTED_LOCALES: tuple[LocaleSpec, ...] = (
    LocaleSpec("de", "Deutsch", "German", "🇩🇪", enabled_by_default=True),
    LocaleSpec("en", "English", "English", "🇬🇧", enabled_by_default=True),
    LocaleSpec("tr", "Türkçe", "Turkish", "🇹🇷"),
    LocaleSpec("ru", "Русский", "Russian", "🇷🇺"),
    LocaleSpec("uk", "Українська", "Ukrainian", "🇺🇦"),
    LocaleSpec("pl", "Polski", "Polish", "🇵🇱"),
    LocaleSpec("ro", "Română", "Romanian", "🇷🇴"),
)
"""The one list of locales: it seeds ``supported_locale`` rows and validates JSONB locale keys.

The ``supported_locale.enabled`` column, not this list, decides which locales are served.
"""

SUPPORTED_LOCALE_CODES: frozenset[str] = frozenset(spec.code for spec in SUPPORTED_LOCALES)
DEFAULT_ENABLED_LOCALES: frozenset[str] = frozenset(spec.code for spec in SUPPORTED_LOCALES if spec.enabled_by_default)


def fallback_chain(locale: str) -> tuple[str, ...]:
    """Return the codes to try for a reader of ``locale``, without repeats.

    German readers get ``de, en``; every other reader gets ``locale, en, de``.
    """
    return tuple(dict.fromkeys((locale, "en", DEFAULT_LOCALE)))


@dataclass(frozen=True, slots=True)
class ResolvedLocale:
    """The negotiated locale code plus the enabled codes available as fallbacks."""

    code: str
    enabled: set[str]


def provide_resolved_locale(request: Request) -> ResolvedLocale:
    """Read the middleware-resolved locale and the app's enabled locale codes."""
    state = request.scope.get("state") or {}
    enabled = getattr(request.app.state, "enabled_locale_codes", DEFAULT_ENABLED_LOCALES)
    return ResolvedLocale(code=str(state.get("locale", DEFAULT_LOCALE)), enabled=set(enabled))
