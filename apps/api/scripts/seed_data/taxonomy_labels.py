"""Check and apply the category label translations of ``taxonomy_translations.py``."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from app.shared.locale import SUPPORTED_LOCALE_CODES

SOURCE_LOCALES = frozenset({"de", "en"})
Labels = Mapping[str, Mapping[str, tuple[str, str]]]
"""Category code to locale to ``(name, description)``."""


def validate_labels(labels: Labels, codes: Iterable[str]) -> None:
    """Raise :class:`ValueError` naming the culprit when ``labels`` would write a wrong code, locale or blank text."""
    unknown = sorted(set(labels) - set(codes))
    if unknown:
        raise ValueError(f"taxonomy_translations names unknown categories: {', '.join(unknown)}")
    allowed = SUPPORTED_LOCALE_CODES - SOURCE_LOCALES
    for code, locales in labels.items():
        _validate_category(code, locales, allowed)


def _validate_category(code: str, locales: Mapping[str, tuple[str, str]], allowed: frozenset[str]) -> None:
    for locale, texts in locales.items():
        if locale not in allowed:
            raise ValueError(
                f"taxonomy_translations: {code!r} has locale {locale!r}; only {sorted(allowed)} may be added"
            )
        if not all(text.strip() for text in texts):
            raise ValueError(f"taxonomy_translations: {code!r} has a blank {locale} text")


def merged_names(base: Mapping[str, str], locales: Mapping[str, tuple[str, str]]) -> dict[str, str]:
    """Return ``base`` plus each locale's name."""
    return {**base, **{locale: name for locale, (name, _description) in locales.items()}}


def merged_descriptions(base: Mapping[str, str], locales: Mapping[str, tuple[str, str]]) -> dict[str, str]:
    """Return ``base`` plus each locale's description."""
    return {**base, **{locale: description for locale, (_name, description) in locales.items()}}
