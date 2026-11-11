"""Build candidate cards from repository rows and the context loaded for a page."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from app.features.candidates.localize import localized
from app.features.candidates.repository import CardRow, DescriptionRow, ScoredCode, TranslationIndexRow
from app.features.candidates.translation_summary import translation_summary
from app.features.search.scoring import displayed_score
from app.features.search.similarity import rescaled_similarity
from app.features.translation.unit import TranslationUnit
from app.models.discovery import DiscoveryDocumentCandidate as Candidate
from app.schema.candidate import CandidateCard, CandidateTranslationSummary
from app.schema.taxonomy.read import CategoryTagRead
from app.shared.locale import ResolvedLocale

DESCRIPTION_MAX_LENGTH = 300


@dataclass(frozen=True, slots=True)
class CardContext:
    """What a page of cards needs besides the rows: locale, category scores, descriptions, translations, names, cut-off."""

    locale: ResolvedLocale
    tag_scores: Mapping[UUID, tuple[ScoredCode, ...]]
    descriptions: Mapping[UUID, DescriptionRow]
    translations: Mapping[UUID, TranslationIndexRow]
    category_names: Mapping[str, str]
    min_similarity: float

    def describe(self, candidate_id: UUID) -> tuple[str | None, str | None]:
        """Return the description (cut to 300 characters) and the title of its procedure, or two ``None``."""
        row = self.descriptions.get(candidate_id)
        if row is None:
            return None, None
        return row.excerpt[:DESCRIPTION_MAX_LENGTH], localized(row.procedure_title_i18n, self.locale)

    def translation_of(self, candidate: Candidate, description: str | None) -> CandidateTranslationSummary | None:
        """Return the translation summary of ``candidate`` shown with ``description``, measured against its German unit."""
        unit = TranslationUnit.of_card(candidate.title_i18n, description)
        return translation_summary(self.translations.get(candidate.id), unit)


def _category_tags(scored: tuple[ScoredCode, ...], names: Mapping[str, str]) -> list[CategoryTagRead]:
    """Map scored canonical categories to localized category tags."""
    return [CategoryTagRead(code=code, name=names.get(code, code), confidence=score) for code, score in scored]


def card_for(row: CardRow, context: CardContext) -> CandidateCard:
    """Return the public card of ``row`` with its localized title, categories and confidence."""
    candidate = row.candidate
    description, source = context.describe(candidate.id)
    return CandidateCard(
        id=candidate.id,
        key=candidate.key,
        title=localized(candidate.title_i18n, context.locale),
        description=description,
        description_source=source,
        categories=_category_tags(context.tag_scores.get(candidate.id, ()), context.category_names),
        mention_count=row.mention_count,
        confidence=row.confidence,
        score=displayed_score(row.score),
        similarity=rescaled_similarity(row.cosine, context.min_similarity),
        translation=context.translation_of(candidate, description),
    )
