"""Which translation tasks each engine may claim: the tail engine takes the first translations of the tail locales in its band, Azure takes the rest."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Final

from sqlalchemy import ColumnElement, and_, false, not_

from app.config import settings
from app.features.translation.priority import FIRST_CEILING, PriorityRange
from app.models.translation import TranslationTask
from app.schema.translation.machine import TranslationClaimRequest

AZURE_ENGINE: Final = "azure-translator"
"""The name the Azure adapter registers under; its claims take the Azure lane."""
TAIL_ENGINE: Final = "llm"
"""The name the Workers AI adapter registers under; its claims take the tail lane only."""


@dataclass(frozen=True, slots=True)
class ClaimScope:
    """What one claim may take: the lane of ``engine`` (no lane when it has none) and a priority band."""

    engine: str | None = None
    priority: PriorityRange = field(default_factory=PriorityRange)


def _band_clauses(band: PriorityRange) -> tuple[ColumnElement[bool], ...]:
    lower = TranslationTask.priority >= band.minimum
    if band.maximum is None:
        return (lower,)
    return (lower, TranslationTask.priority <= band.maximum)


def tail_clause() -> ColumnElement[bool]:
    """Return the predicate of a task the tail engine takes: a tail locale, in the tail band up to the first ceiling."""
    locales = settings.translation_tail_locale_codes
    in_tail = TranslationTask.locale.in_(locales) if locales else false()
    return and_(in_tail, *_band_clauses(PriorityRange(settings.translation_tail_priority_min, FIRST_CEILING)))


def azure_clause() -> ColumnElement[bool]:
    """Return the predicate of a task Azure takes: every task the tail engine does not take."""
    return not_(tail_clause())


LANES: Final[Mapping[str, Callable[[], ColumnElement[bool]]]] = {
    AZURE_ENGINE: azure_clause,
    TAIL_ENGINE: tail_clause,
}
"""The lane of each engine that has one; an engine absent from this table claims without a lane, as before."""


def scope_clauses(scope: ClaimScope) -> tuple[ColumnElement[bool], ...]:
    """Return the predicates a claim with ``scope`` adds: its engine's lane when it has one, and its priority band."""
    lane = LANES.get(scope.engine) if scope.engine is not None else None
    lane_clauses = () if lane is None else (lane(),)
    return (*lane_clauses, *_band_clauses(scope.priority))


def claim_scope(request: TranslationClaimRequest) -> ClaimScope:
    """Return the scope a machine claim body asks for: its engine and its priority band."""
    return ClaimScope(request.engine, PriorityRange(request.priority_min, request.priority_max))
