"""Decide how a list request is answered: browse, legacy title match, keyword search or hybrid search."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import NamedTuple

from app.features.candidates.repository import PublicCandidateFilter
from app.features.search.params import RetrievalParams
from app.features.search.query import NormalisedQuery, normalise_query
from app.features.search.query_embedder import QueryEmbedder
from app.features.search.retrieval import HybridRetrieval, KeywordRetrieval, Retrieval
from app.schema.search import SearchMode


class SearchPlan(NamedTuple):
    """The filter a list request runs and the search mode its answer is labelled with."""

    card_filter: PublicCandidateFilter
    mode: SearchMode


@dataclass(frozen=True, slots=True)
class SearchPlanner:
    """Turn the ``q`` of a filter into the typed retrieval the repository runs, and name the mode it answers in.

    Without ``hybrid_enabled`` the legacy title match stays in ``q``. Whatever goes wrong with the embedder, the
    answer is keyword retrieval, never an error.
    """

    embedder: QueryEmbedder
    params: RetrievalParams
    hybrid_enabled: bool

    def plan(self, card_filter: PublicCandidateFilter, locale: str) -> SearchPlan:
        """Return the filter to run and the search mode of its answer."""
        if card_filter.q is None:
            return SearchPlan(card_filter, SearchMode.BROWSE)
        if not self.hybrid_enabled:
            return SearchPlan(card_filter, SearchMode.KEYWORD)
        query = normalise_query(card_filter.q, locale)
        if query is None:
            return SearchPlan(replace(card_filter, q=None), SearchMode.BROWSE)
        retrieval = self._retrieval(query)
        return SearchPlan(replace(card_filter, q=None, search=retrieval), retrieval.mode)

    def _retrieval(self, query: NormalisedQuery) -> Retrieval:
        vector = self.embedder.embed(query)
        if vector is None:
            return KeywordRetrieval(query, self.params)
        return HybridRetrieval(query, vector, self.params)
