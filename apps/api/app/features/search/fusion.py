"""Reciprocal Rank Fusion: the only place the legs meet, in one statement and deduplicated by candidate id."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import Float, Select, cast, func, literal, select, union_all
from sqlalchemy.sql.expression import Subquery

from app.features.search.legs import CANDIDATE_ID, COSINE, RANK
from app.features.search.params import RetrievalParams
from app.schema.search import SearchMode


def _contribution(leg: Select, rrf_k: int) -> Select:
    """Return the leg's ``(candidate_id, 1 / (k + rank), cos)`` rows."""
    ranked = leg.subquery()
    share = literal(1.0) / (rrf_k + ranked.c[RANK])
    return select(ranked.c[CANDIDATE_ID], cast(share, Float).label("share"), ranked.c[COSINE])


def fuse(legs: Sequence[Select], params: RetrievalParams, mode: SearchMode) -> Subquery:
    """Return ``(candidate_id, rrf, cos, relevance)`` for the best ``fused_top_k`` candidates of ``legs``.

    ``rrf`` sums ``1 / (k + rank)`` over the legs that returned the candidate; ``relevance`` divides it by the best
    possible score of ``mode`` (every leg ranking the candidate first), so it lies in 0..1.
    """
    shares = union_all(*(_contribution(leg, params.rrf_k) for leg in legs)).subquery()
    rrf = func.sum(shares.c.share).label("rrf")
    cos = func.max(shares.c[COSINE]).label(COSINE)
    relevance = cast(rrf / (mode.legs / (params.rrf_k + 1)), Float).label("relevance")
    pool = select(shares.c[CANDIDATE_ID], rrf, cos, relevance).group_by(shares.c[CANDIDATE_ID])
    return _best_pool(pool, params.fused_top_k)


def _best_pool(pool: Select, size: int) -> Subquery:
    """Return the ``size`` best rows of ``pool``: highest ``rrf``, then highest cosine, then candidate id."""
    columns = pool.selected_columns
    ordered = pool.order_by(columns.rrf.desc(), columns[COSINE].desc().nulls_last(), columns[CANDIDATE_ID])
    return ordered.limit(size).subquery("fused")
