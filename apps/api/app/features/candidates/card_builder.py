"""Build candidate cards from repository rows and the context loaded for a page."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from app.features.candidates.localize import localized
from app.features.candidates.repository import CandidateTagScores, CardRow, DescriptionRow, ScoredCode
from app.schema.candidate import CandidateCard, CandidateTag
from app.schema.taxonomy.read import CategoryTagRead
from app.shared.locale import ResolvedLocale

DESCRIPTION_MAX_LENGTH = 300


@dataclass(frozen=True, slots=True)
class CardContext:
    """What a page of cards needs besides the rows: locale, tag scores, descriptions and names."""

    locale: ResolvedLocale
    tag_scores: Mapping[UUID, CandidateTagScores]
    descriptions: Mapping[UUID, DescriptionRow]
    domain_names: Mapping[str, str]
    situation_names: Mapping[str, str]
    category_names: Mapping[str, str]
    category_scores: Mapping[UUID, tuple[ScoredCode, ...]]

    def describe(self, candidate_id: UUID) -> tuple[str | None, str | None]:
        """Return the description (cut to 300 characters) and the title of its procedure, or two ``None``."""
        row = self.descriptions.get(candidate_id)
        if row is None:
            return None, None
        return row.excerpt[:DESCRIPTION_MAX_LENGTH], localized(row.procedure_title_i18n, self.locale)


def _tags(scored: tuple[ScoredCode, ...], names: Mapping[str, str]) -> list[CandidateTag]:
    return [CandidateTag(code=code, name=names.get(code, code), confidence=score) for code, score in scored]


def _category_tags(scored: tuple[ScoredCode, ...], names: Mapping[str, str]) -> list[CategoryTagRead]:
    """Map canonical candidate scores to localized category tags."""
    return [CategoryTagRead(code=code, name=names.get(code, code), confidence=score) for code, score in scored]


def card_for(row: CardRow, context: CardContext) -> CandidateCard:
    """Return the public card of ``row`` with its localized title, tags and confidence."""
    candidate = row.candidate
    scores = context.tag_scores.get(candidate.id, CandidateTagScores())
    category_scores = context.category_scores.get(candidate.id, ())
    description, source = context.describe(candidate.id)
    return CandidateCard(
        id=candidate.id,
        key=candidate.key,
        title=localized(candidate.title_i18n, context.locale),
        description=description,
        description_source=source,
        domains=_tags(scores.domains, context.domain_names),
        situations=_tags(scores.situations, context.situation_names),
        categories=_category_tags(category_scores, context.category_names),
        mention_count=row.mention_count,
        confidence=row.confidence,
    )
