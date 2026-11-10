"""The canonical search text of one candidate: a pure recipe with no database access (recipe ``v1``)."""

from __future__ import annotations

import unicodedata
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from app.features.search.hashing import content_hash
from app.i18n_resolution import pick_i18n
from app.shared.locale import ResolvedLocale

MAX_EXCERPTS: Final = 4
"""Best mention excerpts that follow the title."""
MAX_CHARS: Final = 1500
"""Length limit of the whole text, cut on a word boundary."""

TS_CONFIG_BY_LOCALE: Final[Mapping[str, str]] = {
    "de": "german",
    "en": "english",
    "tr": "turkish",
    "ru": "russian",
    "ro": "romanian",
    "pl": "simple",
    "uk": "simple",
}
"""Text-search configuration of ``tsv_native`` per locale; Postgres has no Polish or Ukrainian one."""


@dataclass(frozen=True, slots=True)
class MentionExcerpt:
    """The excerpt of one mention and the score that ranks it; ``None`` ranks last."""

    id: uuid.UUID
    excerpt: str
    score: float | None


@dataclass(frozen=True, slots=True)
class BuiltText:
    """A search text, its locale and the hash that identifies it."""

    locale: str
    text: str
    content_hash: str


def normalise(text: str) -> str:
    """Return ``text`` in Unicode NFC with every run of whitespace collapsed to one space."""
    return " ".join(unicodedata.normalize("NFC", text).split())


def truncate(text: str, limit: int = MAX_CHARS) -> str:
    """Cut ``text`` to ``limit`` characters on a word boundary; a single overlong word is cut at the limit."""
    if len(text) <= limit:
        return text
    head = text[:limit]
    if text[limit] == " ":
        return head
    return head.rpartition(" ")[0] or head


def _score_order(mention: MentionExcerpt) -> tuple[bool, float, uuid.UUID]:
    """Sort key: scored before unscored, higher score first, then the mention id."""
    return (mention.score is None, -(mention.score or 0.0), mention.id)


def best_excerpts(mentions: Iterable[MentionExcerpt], limit: int = MAX_EXCERPTS) -> list[str]:
    """Return the non-blank excerpts of the ``limit`` best mentions."""
    ranked = sorted(mentions, key=_score_order)
    return [excerpt for mention in ranked if (excerpt := normalise(mention.excerpt))][:limit]


def build(title_i18n: Mapping[str, str], mentions: Sequence[MentionExcerpt], locale: str) -> BuiltText | None:
    """Return the search text of ``locale`` from the title and best excerpts, or ``None`` when there is no text."""
    title = normalise(pick_i18n(title_i18n, ResolvedLocale(locale, set())))
    text = truncate(" ".join(part for part in (title, *best_excerpts(mentions)) if part))
    return BuiltText(locale, text, content_hash(text)) if text else None
