"""The retrievals a search can run: a typed value the service chooses, so no repository branches on a flag."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Protocol

from sqlalchemy import Select
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import Subquery

from app.features.search.fusion import fuse
from app.features.search.keyword import keyword_leg
from app.features.search.params import RetrievalParams
from app.features.search.query import NormalisedQuery
from app.features.search.query_embedder import QueryVector
from app.features.search.vector import vector_leg
from app.features.search.vector_scan import apply_vector_scan
from app.schema.search import SearchMode


class Retrieval(Protocol):
    """A way to find candidates for a query: its mode, its legs within a scope and its session settings."""

    mode: ClassVar[SearchMode]

    @property
    def params(self) -> RetrievalParams:
        """The tunable numbers of this retrieval."""
        ...

    def legs(self, scope: Select | None) -> list[Select]:
        """Return the legs, restricted to the candidate ids ``scope`` selects when it is given."""
        ...

    def prepare(self, session: Session) -> None:
        """Apply the session settings the legs need before the statement runs."""
        ...


@dataclass(frozen=True)
class KeywordRetrieval:
    """Full-text search alone: the flag is off or the query could not be embedded."""

    query: NormalisedQuery
    params: RetrievalParams
    mode: ClassVar[SearchMode] = SearchMode.KEYWORD

    def legs(self, scope: Select | None) -> list[Select]:
        """Return the keyword leg."""
        return [keyword_leg(self.query, self.params, scope)]

    def prepare(self, session: Session) -> None:
        """Nothing to set: the keyword leg reads GIN indexes with the default planner settings."""


@dataclass(frozen=True)
class HybridRetrieval:
    """Full-text and vector search fused: the query was embedded."""

    query: NormalisedQuery
    vector: QueryVector
    params: RetrievalParams
    mode: ClassVar[SearchMode] = SearchMode.HYBRID

    def legs(self, scope: Select | None) -> list[Select]:
        """Return the keyword leg and the vector leg."""
        keyword = keyword_leg(self.query, self.params, scope)
        return [keyword, vector_leg(self.vector, self.query.locale, self.params, scope)]

    def prepare(self, session: Session) -> None:
        """Choose the vector scan: iterative HNSW, or an exact scan when the index is off or unsupported."""
        apply_vector_scan(session, index_enabled=self.params.vector_index_enabled)


def fused_relation(retrieval: Retrieval, scope: Select | None) -> Subquery:
    """Return the fused pool ``(candidate_id, rrf, cos, relevance)`` of ``retrieval``."""
    return fuse(retrieval.legs(scope), retrieval.params, retrieval.mode)
