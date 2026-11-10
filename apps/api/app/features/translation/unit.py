"""The translation unit of a candidate: the German title and the card description, and the hash that marks it stale."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.features.translation.source_hash import source_hash


@dataclass(frozen=True, slots=True)
class TranslationUnit:
    """The two German fields a card shows; they are the only text that is translated."""

    title: str
    description: str

    @property
    def source_hash(self) -> str:
        """Return the hash of this unit under the configured recipe version; a stored translation at another hash is stale."""
        return source_hash(self.title, self.description, recipe_version=settings.translation_unit_recipe_version)
