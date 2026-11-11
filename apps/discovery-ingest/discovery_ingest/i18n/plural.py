"""Plural families: the categories each target locale needs, and the expansion of the source's one/other forms."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Final

from discovery_ingest.i18n.strings import SourceString

PLURAL_SUFFIX: Final = re.compile(r"_(zero|one|two|few|many|other)$")
PLURAL_CATEGORIES: Final[dict[str, tuple[str, ...]]] = {
    "tr": ("one", "other"),
    "ru": ("one", "few", "many", "other"),
    "uk": ("one", "few", "many", "other"),
    "pl": ("one", "few", "many", "other"),
    "ro": ("one", "few", "other"),
}
"""The categories ``Intl.PluralRules`` selects for each locale (CLDR); the web parity test checks the files against ``Intl``."""
CATEGORY_EXAMPLES: Final[dict[str, dict[str, str]]] = {
    "tr": {"one": "1", "other": "0, 2, 3 and every other count"},
    "ru": {
        "one": "1, 21, 31",
        "few": "2, 3, 4, 22, 23, 24",
        "many": "0, 5 to 20, 25 to 30",
        "other": "fractions such as 1.5",
    },
    "uk": {
        "one": "1, 21, 31",
        "few": "2, 3, 4, 22, 23, 24",
        "many": "0, 5 to 20, 25 to 30",
        "other": "fractions such as 1.5",
    },
    "pl": {"one": "1", "few": "2, 3, 4, 22, 23, 24", "many": "0, 5 to 21, 25 to 31", "other": "fractions such as 1.5"},
    "ro": {"one": "1", "few": "0, 2 to 19, 101 to 119", "other": "20 and above, as in '20 de ...'"},
}
"""Counts of each category, for the model: it inflects the noun for them (CLDR integer samples)."""


def family_bases(keys: Iterable[str]) -> frozenset[str]:
    """Return the bases of the plural families in ``keys``: ``x`` for ``x_other`` unless ``x`` is itself a key."""
    present = set(keys)
    bases = {PLURAL_SUFFIX.sub("", key) for key in present if key.endswith("_other")}
    return frozenset(base for base in bases if base not in present)


def categories_of(locale: str) -> tuple[str, ...]:
    """Return the plural categories ``locale`` needs; an unknown locale raises :class:`KeyError`."""
    try:
        return PLURAL_CATEGORIES[locale]
    except KeyError:
        raise KeyError(f"no plural categories known for locale {locale!r}") from None


def _form(base: str, category: str, locale: str, forms: Mapping[str, SourceString]) -> SourceString:
    """Return the string for ``category``: the source's own form when it has one, else its ``other`` form."""
    origin = forms.get(f"{base}_{category}") or forms[f"{base}_other"]
    note = f"plural form '{category}' of '{base}', used for counts such as {CATEGORY_EXAMPLES[locale][category]}"
    return SourceString(f"{base}_{category}", origin.german, origin.english, note)


def expand_plurals(strings: Sequence[SourceString], locale: str) -> list[SourceString]:
    """Replace each plural family of ``strings`` by one string per category ``locale`` needs; others pass through."""
    categories = categories_of(locale)
    by_key = {string.key: string for string in strings}
    bases = family_bases(by_key)
    expanded: list[SourceString] = []
    done: set[str] = set()
    for string in strings:
        base = PLURAL_SUFFIX.sub("", string.key)
        if base not in bases:
            expanded.append(string)
        elif base not in done:
            done.add(base)
            expanded.extend(_form(base, category, locale, by_key) for category in categories)
    return expanded
