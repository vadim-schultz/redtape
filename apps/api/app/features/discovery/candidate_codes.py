"""Keep the taxonomy codes a mention batch names and count the ones the vocabulary lacks."""

from __future__ import annotations

from dataclasses import dataclass

from app.features.taxonomy.service import TaxonomyService
from app.schema.discovery.candidates import CandidateMentionItem


@dataclass(frozen=True, slots=True)
class ItemCodes:
    """The codes of one item that exist in the vocabulary, and how many were dropped."""

    domain_codes: list[str] | None
    situation_codes: list[str] | None
    dropped: int


def _keep(known: set[str], codes: list[str] | None) -> tuple[list[str] | None, int]:
    if codes is None:
        return None, 0
    kept = [code for code in codes if code in known]
    return kept, len(codes) - len(kept)


@dataclass(frozen=True, slots=True)
class CodeVocabulary:
    """The domain and situation codes of one batch that the taxonomy knows."""

    domains: set[str]
    situations: set[str]

    @classmethod
    def for_items(cls, items: list[CandidateMentionItem], taxonomy: TaxonomyService) -> CodeVocabulary:
        """Look the codes of every item up once for the whole batch."""
        domains = {code for item in items for code in item.domain_codes or []}
        situations = {code for item in items for code in item.situation_codes or []}
        return cls(taxonomy.known_domain_codes(domains), taxonomy.known_situation_codes(situations))

    def filter(self, item: CandidateMentionItem) -> ItemCodes:
        """Return ``item``'s known codes; unknown ones are dropped and counted."""
        domains, dropped_domains = _keep(self.domains, item.domain_codes)
        situations, dropped_situations = _keep(self.situations, item.situation_codes)
        return ItemCodes(domains, situations, dropped_domains + dropped_situations)
