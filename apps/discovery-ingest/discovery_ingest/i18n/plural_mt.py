"""Representative numbers for machine plural forms: a CLDR sample count stands in for ``{count}``, then goes back.

A machine translator receives no inflection note, so it cannot know which count a plural form is for. The sample
number says it instead: the engine inflects the noun for the number it is given, and the number is replaced by
``{count}`` again. :mod:`discovery_ingest.i18n.plural` keeps the note for the engines that read it.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Final

from discovery_ingest.i18n.plural import PLURAL_SUFFIX
from discovery_ingest.translation import tokens

COUNT: Final = "{count}"
_EAST_SLAVIC: Final[Mapping[str, tuple[str, ...]]] = {
    "one": ("1", "21"),
    "few": ("2", "3", "4", "22"),
    "many": ("5", "11", "25"),
    "other": ("1,5", "1,2", "3,4"),
}
SAMPLES: Final[Mapping[str, Mapping[str, tuple[str, ...]]]] = {
    "tr": {"one": ("1",), "other": ("2", "3", "0")},
    "ru": _EAST_SLAVIC,
    "uk": _EAST_SLAVIC,
    "pl": {
        "one": ("1",),
        "few": ("2", "3", "4", "22"),
        "many": ("5", "11", "21", "25"),
        "other": ("1,5", "1,2", "3,4"),
    },
    "ro": {"one": ("1",), "few": ("2", "3", "19"), "other": ("20", "21", "100")},
}
"""The sample counts of each category, most typical first; a fraction stands for the ``other`` of a Slavic language.

The categories are those ``Intl.PluralRules`` selects (see :data:`~discovery_ingest.i18n.plural.PLURAL_CATEGORIES`).
"""


def representative_for(locale: str, key: str, text: str) -> str | None:
    """Return the sample count for the plural form ``key`` with German ``text`` in ``locale``; ``None`` if none applies.

    No sample applies to a key that is not a plural form, to a text without ``{count}``, or when every sample of the
    category is a number the text already has, so a sample is never mistaken for a real number.
    """
    match = PLURAL_SUFFIX.search(key)
    if match is None or COUNT not in text:
        return None
    candidates = SAMPLES.get(locale, {}).get(match.group(1), ())
    return next((sample for sample in candidates if not _numbers(sample) & _numbers(text)), None)


def restore_count(text: str, sample: str | None) -> str:
    """Put ``{count}`` back in place of ``sample``; the sample inside a longer number, or a token, is not touched."""
    if sample is None:
        return text
    return _whole_number(sample).sub(COUNT, text)


def _numbers(text: str) -> frozenset[str]:
    return frozenset(tokens.NUMBER.findall(text))


def _whole_number(sample: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![\d.,⟦]){re.escape(sample)}(?![\d⟧]|[.,]\d)")
