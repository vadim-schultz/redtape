"""Accepted tag codes per candidate in SQL: the ``aggregate_tags`` rule, replaced by manual mentions (D6, D18)."""

from __future__ import annotations

import enum
from dataclasses import dataclass

from sqlalchemy import ColumnElement, Float, and_, cast, distinct, func, select
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql.expression import CTE, Select, Subquery
from sqlalchemy.sql.functions import array_agg

from app.config import Settings
from app.features.discovery.tags import MANUAL_EXTRACTOR
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


class TagAxis(enum.Enum):
    """A tag axis of a mention: the array column that carries its codes."""

    DOMAIN = "domain"
    SITUATION = "situation"

    @property
    def column(self) -> InstrumentedAttribute[list[str] | None]:
        """Return the mention column holding this axis' codes."""
        return Mention.domain_codes if self is TagAxis.DOMAIN else Mention.situation_codes


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


def _consensus(exploded: CTE, thresholds: TagThresholds) -> Select:
    support, tagged = _support(exploded), _tagged(exploded)
    joined = support.join(tagged, tagged.c.candidate_id == support.c.candidate_id)
    stmt = select(support.c.candidate_id, _sorted_codes(support.c.code).label("codes")).select_from(joined)
    return stmt.where(_meets(support, tagged, thresholds)).group_by(support.c.candidate_id)


def _manual_branch(exploded: CTE) -> Select:
    stmt = select(exploded.c.candidate_id, _sorted_codes(exploded.c.code).label("codes"))
    return stmt.where(exploded.c.extractor == MANUAL_EXTRACTOR).group_by(exploded.c.candidate_id)


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
