"""Keep the taxonomy codes a mention batch names and count the ones the vocabulary lacks."""

from __future__ import annotations

from dataclasses import dataclass

from app.features.taxonomy.service import TaxonomyService
from app.schema.discovery.candidates import CandidateMentionItem


@dataclass(frozen=True, slots=True)
class ItemCodes:
    """The codes of one item that exist in the vocabulary, and how many were dropped."""

    category_codes: list[str] | None
    dropped: int


def _keep(known: set[str], codes: list[str] | None) -> tuple[list[str] | None, int]:
    if codes is None:
        return None, 0
    kept = [code for code in codes if code in known]
    return kept, len(codes) - len(kept)


@dataclass(frozen=True, slots=True)
class CodeVocabulary:
    """The canonical category codes of one batch that the taxonomy knows."""

    categories: set[str]

    @classmethod
    def for_items(cls, items: list[CandidateMentionItem], taxonomy: TaxonomyService) -> CodeVocabulary:
        """Look the codes of every item up once for the whole batch."""
        categories = {code for item in items for code in item.category_codes or []}
        return cls(taxonomy.known_category_codes(categories))

    def filter(self, item: CandidateMentionItem) -> ItemCodes:
        """Return ``item``'s known codes; unknown ones are dropped and counted."""
        categories, dropped = _keep(self.categories, item.category_codes)
        return ItemCodes(categories, dropped)
