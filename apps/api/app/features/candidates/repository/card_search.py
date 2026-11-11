"""What a search adds to a card query: the fused pool it joins, its columns, its score and its session settings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import ColumnElement, Select
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import Subquery

from app.features.search.retrieval import Retrieval
from app.features.search.scoring import combined_expression
from app.models.discovery import DiscoveryDocumentCandidate as Candidate


class CardSearch(Protocol):
    """The search side of a card query: a browse adds nothing, a search joins its fused pool."""

    @property
    def relevance(self) -> ColumnElement[float] | None:
        """The relevance column of the pool, or ``None`` without a search."""
        ...

    @property
    def columns(self) -> list[ColumnElement[float]]:
        """The columns a page selects besides the card's own: relevance and cosine, or none."""
        ...

    def prepare(self, session: Session) -> None:
        """Apply the session settings the search needs."""
        ...

    def join(self, stmt: Select) -> Select:
        """Restrict a select over candidates to the search's pool, so the list and its count read the same rows."""
        ...

    def score(self, confidence: ColumnElement[float]) -> ColumnElement[float]:
        """Return the ranking score over ``confidence``: the combined score of a search, else the confidence."""
        ...


@dataclass(frozen=True, slots=True)
class NoSearch:
    """A browse: every candidate is listed, ranked by confidence."""

    @property
    def relevance(self) -> None:
        """A browse has no relevance."""
        return None

    @property
    def columns(self) -> list[ColumnElement[float]]:
        """A browse selects no search columns."""
        return []

    def prepare(self, session: Session) -> None:
        """Nothing to set."""

    def join(self, stmt: Select) -> Select:
        """Keep ``stmt`` as it is."""
        return stmt

    def score(self, confidence: ColumnElement[float]) -> ColumnElement[float]:
        """Return the confidence itself."""
        return confidence


@dataclass(frozen=True, slots=True)
class FusedSearch:
    """A search's retrieval and the fused pool ``(candidate_id, rrf, cos, relevance)`` its legs produced."""

    retrieval: Retrieval
    pool: Subquery

    @property
    def relevance(self) -> ColumnElement[float]:
        """The relevance column of the pool."""
        return self.pool.c.relevance

    @property
    def columns(self) -> list[ColumnElement[float]]:
        """The relevance and cosine columns of the pool."""
        return [self.pool.c.relevance, self.pool.c.cos]

    def prepare(self, session: Session) -> None:
        """Apply the session settings of the retrieval."""
        self.retrieval.prepare(session)

    def join(self, stmt: Select) -> Select:
        """Keep only the candidates of the pool."""
        return stmt.join(self.pool, self.pool.c.candidate_id == Candidate.id)

    def score(self, confidence: ColumnElement[float]) -> ColumnElement[float]:
        """Return the combined score of the pool's relevance and ``confidence``."""
        return combined_expression(self.relevance, confidence, self.retrieval.params.confidence_weight)
