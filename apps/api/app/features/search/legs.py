"""The contract between the retrieval legs and the fusion: the three columns every leg selects."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from sqlalchemy import ColumnElement, Float, Select, cast, func, null, select
from sqlalchemy.sql.expression import Subquery

CANDIDATE_ID: Final = "candidate_id"
RANK: Final = "rnk"
COSINE: Final = "cos"
"""The cosine similarity of a vector hit; ``NULL`` for a leg that has none."""


def ranked_leg(
    hits: Subquery, order_by: Sequence[ColumnElement[object]], cosine: ColumnElement[float] | None
) -> Select:
    """Return ``hits`` as a leg: ``(candidate_id, rank by order_by, cosine)``; ``cosine`` ``None`` selects ``NULL``."""
    rank = func.row_number().over(order_by=tuple(order_by)).label(RANK)
    similarity = null() if cosine is None else cosine
    return select(hits.c[CANDIDATE_ID], rank, cast(similarity, Float).label(COSINE))
