"""The translation unit of a candidate: the German title and the card description, and the hash that marks it stale."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from app.config import settings
from app.features.translation.source_hash import source_hash
from app.shared.locale import DEFAULT_LOCALE


def german_title(title_i18n: Mapping[str, str] | None) -> str:
    """Return the trimmed German title of a candidate, or ``""`` when it has none."""
    return (title_i18n or {}).get(DEFAULT_LOCALE, "").strip()


@dataclass(frozen=True, slots=True)
class TranslationUnit:
    """The two German fields a card shows; they are the only text that is translated."""

    title: str
    description: str

    @classmethod
    def of_card(cls, title_i18n: Mapping[str, str] | None, description: str | None) -> TranslationUnit:
        """Return the unit of a card: its German title and its description as shown, empty without one."""
        return cls(german_title(title_i18n), description or "")

    @property
    def source_hash(self) -> str:
        """Return the hash of this unit under the configured recipe version; a stored translation at another hash is stale."""
        return source_hash(self.title, self.description, recipe_version=settings.translation_unit_recipe_version)

    def is_stale(self, indexed_hash: str) -> bool:
        """Return whether a translation made from the unit hashed ``indexed_hash`` no longer matches this unit."""
        return indexed_hash != self.source_hash
