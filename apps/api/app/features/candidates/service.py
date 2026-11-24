"""Public candidate reads: the ranked list and the detail with its neighbours."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from uuid import UUID

from app.config import settings
from app.features.candidates.card_builder import CardContext, card_for
from app.features.candidates.detail import Evidence, detail_of
from app.features.candidates.links import public_url
from app.features.candidates.repository import CardRow, PublicCandidateFilter, PublicCandidateRepository
from app.features.candidates.search_plan import SearchPlanner
from app.features.discovery.errors import CandidateNotFoundError
from app.features.discovery.repository import EdgeRow, Page
from app.features.taxonomy.service import TaxonomyService
from app.schema.candidate import CandidateDetail, CandidateListResponse
from app.shared.list_query.errors import InvalidParam, raise_if_any
from app.shared.locale import ResolvedLocale


@dataclass(frozen=True, slots=True)
class BestMention:
    """The procedure page behind a candidate's card excerpt, and that page's web link when it has a usable one."""

    catalogue_service_id: UUID
    source_url: str | None


def _ends(edges: Sequence[EdgeRow], candidate_id: UUID) -> list[UUID]:
    """Return the ids of the candidates on the far side of ``edges``."""
    return list({end.id for row in edges for end in (row.parent, row.required)} - {candidate_id})


def _unknown_codes(key: str, codes: Sequence[str], known: Callable[[Sequence[str]], set[str]]) -> list[InvalidParam]:
    """Return one error per code of ``codes`` that ``known`` does not recognise, in request order."""
    recognised = known(codes) if codes else set()
    return [InvalidParam(key, f"Unknown code: {code}") for code in codes if code not in recognised]


class CandidateReadService:
    """Read staged candidates for anyone: cards ranked by completeness, and one candidate with its evidence."""

    def __init__(self, repository: PublicCandidateRepository, taxonomy: TaxonomyService, search: SearchPlanner) -> None:
        """Bind the service to the public ``repository``, the taxonomy lookups and the ``search`` planner."""
        self._repo = repository
        self._taxonomy = taxonomy
        self._search = search

    def list_candidates(
        self, card_filter: PublicCandidateFilter, page: Page, locale: ResolvedLocale
    ) -> CandidateListResponse:
        """Return one page of cards; an unknown category code in the filter is a validation error."""
        card_filter, mode = self._search.plan(self._resolve_filter(card_filter), locale.code)
        rows = self._repo.list_card_rows(card_filter, page)
        context = self._context([row.candidate.id for row in rows], locale)
        items = [card_for(row, context) for row in rows]
        total = self._repo.count_cards(card_filter)
        return CandidateListResponse(items=items, total=total, offset=page.offset, limit=page.limit, search_mode=mode)

    def candidate_detail(self, candidate_id: UUID, locale: ResolvedLocale) -> CandidateDetail:
        """Return one candidate with ingress, egress, sources and screenshot reference; 404 when unknown."""
        row = self._require_row(candidate_id)
        edges = self._repo.list_candidate_edges(candidate_id)
        context = self._context([candidate_id, *_ends(edges, candidate_id)], locale)
        return detail_of(card_for(row, context), self._evidence(candidate_id, edges), context)

    def best_mention(self, candidate_id: UUID) -> BestMention | None:
        """Return the page of the mention whose excerpt the card shows, or ``None`` when there is none; 404 when unknown."""
        self._require_row(candidate_id)
        row = self._repo.best_descriptions([candidate_id]).get(candidate_id)
        return None if row is None else BestMention(row.catalogue_service_id, public_url(row.source_url))

    def _require_row(self, candidate_id: UUID) -> CardRow:
        row = self._repo.get_card_row(candidate_id)
        if row is None:
            raise CandidateNotFoundError()
        return row

    def _evidence(self, candidate_id: UUID, edges: Sequence[EdgeRow]) -> Evidence:
        mentions = self._repo.list_candidate_mentions(candidate_id)
        screenshots = self._repo.list_screenshots(candidate_id, settings.screenshot_keep_per_page)
        return Evidence(edges, mentions, screenshots)

    def _context(self, candidate_ids: Sequence[UUID], locale: ResolvedLocale) -> CardContext:
        return CardContext(
            locale=locale,
            tag_scores=self._repo.tag_scores_for(candidate_ids),
            descriptions=self._repo.best_descriptions(candidate_ids),
            translations=self._repo.translations_for(candidate_ids, locale.code),
            category_names=self._taxonomy.category_names(locale=locale),
            min_similarity=self._search.params.min_similarity,
        )

    def _resolve_filter(self, card_filter: PublicCandidateFilter) -> PublicCandidateFilter:
        """Reject unknown category codes, then expand each selected category to its active descendants."""
        raise_if_any(
            _unknown_codes("filter[category]", card_filter.category_codes, self._taxonomy.known_category_codes)
        )
        if not card_filter.category_codes:
            return card_filter
        return replace(card_filter, category_codes=self._taxonomy.expand_category_codes(card_filter.category_codes))
