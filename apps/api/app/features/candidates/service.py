"""Public candidate reads: the ranked list and the detail with its neighbours."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from uuid import UUID

from app.features.candidates.card_builder import CardContext, card_for
from app.features.candidates.detail import Evidence, detail_of
from app.features.candidates.repository import CardRow, PublicCandidateFilter, PublicCandidateRepository
from app.features.discovery.errors import CandidateNotFoundError
from app.features.discovery.repository import EdgeRow, Page
from app.features.taxonomy.service import TaxonomyService
from app.schema.candidate import CandidateDetail, CandidateListResponse
from app.schema.taxonomy.read import TermRead
from app.shared.list_query.errors import InvalidParam, raise_if_any
from app.shared.locale import ResolvedLocale


def _names(terms: Sequence[TermRead]) -> dict[str, str]:
    return {term.code: term.name for term in terms}


def _ends(edges: Sequence[EdgeRow], candidate_id: UUID) -> list[UUID]:
    """Return the ids of the candidates on the far side of ``edges``."""
    return list({end.id for row in edges for end in (row.parent, row.required)} - {candidate_id})


def _unknown_codes(key: str, codes: Sequence[str], known: Callable[[Sequence[str]], set[str]]) -> list[InvalidParam]:
    """Return one error per code of ``codes`` that ``known`` does not recognise, in request order."""
    recognised = known(codes) if codes else set()
    return [InvalidParam(key, f"Unknown code: {code}") for code in codes if code not in recognised]


class CandidateReadService:
    """Read staged candidates for anyone: cards ranked by completeness, and one candidate with its evidence."""

    def __init__(self, repository: PublicCandidateRepository, taxonomy: TaxonomyService) -> None:
        """Bind the service to the public ``repository`` and the taxonomy lookups."""
        self._repo = repository
        self._taxonomy = taxonomy

    def list_candidates(
        self, card_filter: PublicCandidateFilter, page: Page, locale: ResolvedLocale
    ) -> CandidateListResponse:
        """Return one page of cards; an unknown taxonomy code in the filter is a validation error."""
        self._reject_unknown_codes(card_filter)
        rows = self._repo.list_card_rows(card_filter, page)
        context = self._context([row.candidate.id for row in rows], locale)
        items = [card_for(row, context) for row in rows]
        total = self._repo.count_cards(card_filter)
        return CandidateListResponse(items=items, total=total, offset=page.offset, limit=page.limit)

    def candidate_detail(self, candidate_id: UUID, locale: ResolvedLocale) -> CandidateDetail:
        """Return one candidate with ingress, egress, sources and screenshot reference; 404 when unknown."""
        row = self._require_row(candidate_id)
        edges = self._repo.list_candidate_edges(candidate_id)
        context = self._context([candidate_id, *_ends(edges, candidate_id)], locale)
        return detail_of(card_for(row, context), self._evidence(candidate_id, edges), context)

    def _require_row(self, candidate_id: UUID) -> CardRow:
        row = self._repo.get_card_row(candidate_id)
        if row is None:
            raise CandidateNotFoundError()
        return row

    def _evidence(self, candidate_id: UUID, edges: Sequence[EdgeRow]) -> Evidence:
        mentions = self._repo.list_candidate_mentions(candidate_id)
        return Evidence(edges, mentions, self._repo.newest_screenshot(candidate_id))

    def _context(self, candidate_ids: Sequence[UUID], locale: ResolvedLocale) -> CardContext:
        domains = self._taxonomy.list_domains(locale=locale)
        situations = self._taxonomy.list_situations(locale=locale)
        return CardContext(
            locale=locale,
            completeness=self._repo.completeness_for(candidate_ids),
            tag_scores=self._repo.tag_scores_for(candidate_ids),
            descriptions=self._repo.best_descriptions(candidate_ids),
            domain_names=_names(domains),
            situation_names=_names(situations),
        )

    def _reject_unknown_codes(self, card_filter: PublicCandidateFilter) -> None:
        checks = (
            ("filter[domain]", card_filter.domains, self._taxonomy.known_domain_codes),
            ("filter[situation]", card_filter.situations, self._taxonomy.known_situation_codes),
        )
        raise_if_any([error for key, codes, known in checks for error in _unknown_codes(key, codes, known)])
