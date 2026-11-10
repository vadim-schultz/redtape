"""The vector leg: nearest embeddings by cosine distance, cut off below a minimum similarity, one row per candidate."""

from __future__ import annotations

from sqlalchemy import Select, func, select
from sqlalchemy.sql.expression import Subquery

from app.features.search.legs import CANDIDATE_ID, ranked_leg
from app.features.search.params import RetrievalParams
from app.features.search.query_embedder import QueryVector
from app.models.search import CANONICAL_LOCALE
from app.models.search import CandidateEmbedding as Embedding

ROWS_PER_CANDIDATE = 2
"""A candidate has at most a row for the request locale and one for German, so this many rows yield ``top_n`` ids."""


def _nearest(vector: QueryVector, locale: str, params: RetrievalParams, scope: Select | None) -> Subquery:
    """Return the nearest embedding rows ``(candidate_id, dist)``: the shape pgvector needs for an HNSW scan.

    Ordered by the distance operator with a limit. The cut-off is not applied here: inside, a nonsense query that
    nothing passes would make the iterative scan walk the whole index looking for rows that never come.
    """
    distance = Embedding.embedding.cosine_distance(list(vector))
    rows = select(Embedding.candidate_id, distance.label("dist")).where(
        Embedding.model == params.model, Embedding.locale.in_({locale, CANONICAL_LOCALE})
    )
    if scope is not None:
        rows = rows.where(Embedding.candidate_id.in_(scope))
    return rows.order_by(distance).limit(ROWS_PER_CANDIDATE * params.top_n).subquery()


def _best_rows(nearest: Subquery, params: RetrievalParams) -> Subquery:
    """Return the closest row of each candidate within the cut-off, nearest first, at most ``params.top_n``."""
    closest = func.min(nearest.c.dist)
    best = select(nearest.c[CANDIDATE_ID], closest.label("dist")).group_by(nearest.c[CANDIDATE_ID])
    within = best.having(closest <= 1.0 - params.min_similarity).order_by("dist", nearest.c[CANDIDATE_ID])
    return within.limit(params.top_n).subquery()


def vector_leg(vector: QueryVector, locale: str, params: RetrievalParams, scope: Select | None) -> Select:
    """Return the ranked top ``params.top_n`` candidates whose embedding is similar enough to ``vector``.

    The best of a candidate's rows wins; the similarity is ``1 - distance``.
    """
    top = _best_rows(_nearest(vector, locale, params, scope), params)
    return ranked_leg(top, (top.c.dist, top.c[CANDIDATE_ID]), 1.0 - top.c.dist)
