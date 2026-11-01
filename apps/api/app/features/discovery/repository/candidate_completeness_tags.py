"""Accepted tag codes per candidate in SQL: one consensus engine shared by the bulk and single-candidate paths."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import ColumnElement, Float, and_, cast, distinct, func, select
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import CTE, Select, Subquery
from sqlalchemy.sql.functions import array_agg

from app.config import Settings
from app.features.discovery.tags import MANUAL_EXTRACTOR, TagAxis, TagSupport
from app.models.discovery import DiscoveryCandidateMention as Mention


@dataclass(frozen=True)
class TagThresholds:
    """The two thresholds a code needs: distinct procedures, and their share of the tagged procedures."""

    min_procedures: int
    min_share: float

    @classmethod
    def from_settings(cls, source: Settings) -> TagThresholds:
        """Read the thresholds the emit path uses from ``source``."""
        return cls(source.discovery_tag_min_procedures, source.discovery_tag_min_share)


def _exploded(axis: TagAxis) -> CTE:
    code = func.unnest(axis.column).label("code")
    stmt = select(Mention.candidate_id, Mention.catalogue_service_id, Mention.extractor, code)
    return stmt.cte(f"{axis.value}_exploded")


def _support(exploded: CTE) -> Subquery:
    procedures = func.count(distinct(exploded.c.catalogue_service_id))
    keys = (exploded.c.candidate_id, exploded.c.code)
    return select(*keys, procedures.label("procedures")).group_by(*keys).subquery()


def _tagged(exploded: CTE) -> Subquery:
    tagged = func.count(distinct(exploded.c.catalogue_service_id))
    return select(exploded.c.candidate_id, tagged.label("tagged")).group_by(exploded.c.candidate_id).subquery()


def _sorted_codes(code: ColumnElement[str]) -> array_agg[str]:
    return func.array_agg(aggregate_order_by(distinct(code), code))


def _meets(support: Subquery, tagged: Subquery, thresholds: TagThresholds) -> ColumnElement[bool]:
    share = cast(support.c.procedures, Float) / cast(tagged.c.tagged, Float)
    return and_(support.c.procedures >= thresholds.min_procedures, share >= thresholds.min_share)


def code_support(exploded: CTE, thresholds: TagThresholds) -> Select:
    """Return one row per ``(candidate_id, code)``: its procedure count, share, and whether that accepts it.

    Unlike :func:`_consensus`, every code is returned, not only the ones that clear the bar — the single-
    candidate detail path needs the full breakdown, the bulk path filters this down to the accepted ones.
    """
    support, tagged = _support(exploded), _tagged(exploded)
    joined = support.join(tagged, tagged.c.candidate_id == support.c.candidate_id)
    share = cast(support.c.procedures, Float) / cast(tagged.c.tagged, Float)
    cols = (support.c.candidate_id, support.c.code, support.c.procedures, share.label("share"))
    return select(*cols, _meets(support, tagged, thresholds).label("accepted")).select_from(joined)


def _consensus(exploded: CTE, thresholds: TagThresholds) -> Select:
    rows = code_support(exploded, thresholds).subquery()
    stmt = select(rows.c.candidate_id, _sorted_codes(rows.c.code).label("codes"))
    return stmt.where(rows.c.accepted).group_by(rows.c.candidate_id)


def _manual_branch(exploded: CTE) -> Select:
    stmt = select(exploded.c.candidate_id, _sorted_codes(exploded.c.code).label("codes"))
    return stmt.where(exploded.c.extractor == MANUAL_EXTRACTOR).group_by(exploded.c.candidate_id)


def _manual_support(exploded: CTE) -> Select:
    """Return one row per ``(candidate_id, code)`` manually asserted, each with its procedure count.

    The per-code mirror of :func:`_manual_branch`, which aggregates the same rows into one codes array.
    """
    procedures = func.count(distinct(exploded.c.catalogue_service_id))
    keys = (exploded.c.candidate_id, exploded.c.code)
    stmt = select(*keys, procedures.label("procedures")).where(exploded.c.extractor == MANUAL_EXTRACTOR)
    return stmt.group_by(*keys)


def _sorted_supports(supports: list[TagSupport]) -> list[TagSupport]:
    return sorted(supports, key=lambda support: (-support.procedures, support.code))


def axis_acceptance(axis: TagAxis, thresholds: TagThresholds) -> Subquery:
    """Return ``(candidate_id, codes)`` for the candidates with accepted codes on ``axis``.

    The codes of the manual mentions replace the consensus; ``codes`` is sorted and never empty.
    """
    exploded = _exploded(axis)
    manual = _manual_branch(exploded).subquery()
    consensus = _consensus(exploded, thresholds).subquery()
    joined = manual.join(consensus, manual.c.candidate_id == consensus.c.candidate_id, full=True)
    candidate_id = func.coalesce(manual.c.candidate_id, consensus.c.candidate_id)
    codes = func.coalesce(manual.c.codes, consensus.c.codes)
    return select(candidate_id.label("candidate_id"), codes.label("codes")).select_from(joined).subquery()


def candidate_axis_support(
    session: Session, candidate_id: UUID, axis: TagAxis, thresholds: TagThresholds
) -> list[TagSupport]:
    """Return the support of every code of one candidate's mentions on ``axis``, most supported first.

    A manual mention replaces the consensus entirely for the axis, the same way :func:`axis_acceptance`
    replaces it for the bulk path; the direct, single-candidate replacement for the retired pure-Python
    consensus pair this module now supersedes.
    """
    exploded = _exploded(axis)
    manual_stmt = _manual_support(exploded).where(exploded.c.candidate_id == candidate_id)
    manual_rows = session.execute(manual_stmt).all()
    if manual_rows:
        return _sorted_supports([TagSupport(row.code, row.procedures, 1.0, True) for row in manual_rows])
    support_stmt = code_support(exploded, thresholds).subquery()
    rows = session.execute(select(support_stmt).where(support_stmt.c.candidate_id == candidate_id))
    return _sorted_supports([TagSupport(row.code, row.procedures, row.share, row.accepted) for row in rows])
