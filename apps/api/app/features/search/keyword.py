"""The keyword leg: full-text rank over the rows of the request locale and German, plus the legacy title match."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from sqlalchemy import ColumnElement, Select, and_, case, cast, func, or_, select, true
from sqlalchemy.dialects.postgresql import REGCONFIG
from sqlalchemy.orm import QueryableAttribute
from sqlalchemy.sql.expression import Subquery

from app.features.discovery.repository.candidate_filter import title_matches
from app.features.search.legs import CANDIDATE_ID, ranked_leg
from app.features.search.params import RetrievalParams
from app.features.search.query import NormalisedQuery
from app.features.search.text import TS_CONFIG_BY_LOCALE
from app.models.discovery import DiscoveryDocumentCandidate as Candidate
from app.models.search import CANONICAL_LOCALE
from app.models.search import CandidateSearchText as Text

TITLE_BONUS: Final = 1.0
"""Added to the rank of a candidate whose title contains the query, so exact titles never fall behind a text match."""


@dataclass(frozen=True, slots=True)
class _Reading:
    """One way to read a search-text row: the rows it applies to, their vector and the query parsed for it."""

    applies: ColumnElement[bool]
    vector: QueryableAttribute[str]
    query: ColumnElement[str]

    @property
    def matches(self) -> ColumnElement[bool]:
        """The row is in scope for this reading and its vector matches the query."""
        return and_(self.applies, self.vector.op("@@")(self.query))

    @property
    def rank(self) -> ColumnElement[float]:
        """The cover-density rank of the row for this reading, ``0`` for a row it does not apply to."""
        return case((self.applies, func.ts_rank_cd(self.vector, self.query)), else_=0.0)


def _tsquery(config: str, text: str) -> ColumnElement[str]:
    """Return the accent-free web-search tsquery of ``text`` under text-search configuration ``config``."""
    return func.websearch_to_tsquery(cast(config, REGCONFIG), func.unaccent(text))


def _readings(query: NormalisedQuery) -> list[_Reading]:
    """Return the readings: the locale's own configuration, German on the German row, ``simple`` on every row."""
    native = _Reading(
        Text.locale == query.locale,
        Text.tsv_native,
        _tsquery(TS_CONFIG_BY_LOCALE.get(query.locale, "simple"), query.text),
    )
    german = _Reading(Text.locale == CANONICAL_LOCALE, Text.tsv_native, _tsquery("german", query.text))
    simple = _Reading(true(), Text.tsv_simple, _tsquery("simple", query.text))
    return [native, simple] if query.locale == CANONICAL_LOCALE else [native, german, simple]


def _text_scores(query: NormalisedQuery) -> Subquery:
    """Return the subquery ``(candidate_id, score)`` of the best rank of each candidate over its matching rows."""
    readings = _readings(query)
    best = func.greatest(*(reading.rank for reading in readings)).label("score")
    rows = Text.locale.in_({query.locale, CANONICAL_LOCALE})
    stmt = select(Text.candidate_id, func.max(best).label("score")).where(rows, or_(*(r.matches for r in readings)))
    return stmt.group_by(Text.candidate_id).subquery()


def _hits(query: NormalisedQuery, scope: Select | None) -> Select:
    """Return ``(candidate_id, score)`` of every candidate with a text match or a title match, within ``scope``."""
    scores = _text_scores(query)
    title = title_matches(query.text)
    score = func.coalesce(scores.c.score, 0.0) + case((title, TITLE_BONUS), else_=0.0)
    hits = (
        select(Candidate.id.label(CANDIDATE_ID), score.label("score"))
        .outerjoin(scores, scores.c.candidate_id == Candidate.id)
        .where(or_(scores.c.candidate_id.is_not(None), title))
    )
    return hits if scope is None else hits.where(Candidate.id.in_(scope))


def keyword_leg(query: NormalisedQuery, params: RetrievalParams, scope: Select | None) -> Select:
    """Return the ranked top ``params.top_n`` candidates matching ``query``, within ``scope`` when it is given."""
    hits = _hits(query, scope).subquery()
    best = select(hits).order_by(hits.c.score.desc(), hits.c[CANDIDATE_ID]).limit(params.top_n).subquery()
    return ranked_leg(best, (best.c.score.desc(), best.c[CANDIDATE_ID]), None)
