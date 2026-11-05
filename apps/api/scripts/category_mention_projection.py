"""Project legacy mention axis codes into the canonical category columns of ``discovery_candidate_mention``.

The transformation is the same one the application boundary applied before Chapter 9: a stored value that is an
active category code passes through, a legacy value maps through the frozen crosswalk, and anything else is
counted as unknown rather than invented. The direct confidence is the strongest of the two legacy confidences.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

import sqlalchemy as sa
from sqlalchemy import Connection

from scripts.seed_data.taxonomy import CATEGORY_INVENTORY, LEGACY_CROSSWALK

MENTION_TABLE = sa.table(
    "discovery_candidate_mention",
    sa.column("id", sa.Uuid(as_uuid=True)),
    sa.column("domain_codes", sa.ARRAY(sa.String(length=64))),
    sa.column("situation_codes", sa.ARRAY(sa.String(length=64))),
    sa.column("direct_domain_confidence", sa.Float()),
    sa.column("direct_situation_confidence", sa.Float()),
    sa.column("category_codes", sa.ARRAY(sa.String(length=64))),
    sa.column("direct_category_confidence", sa.Float()),
)

ACTIVE_CATEGORY_CODES = frozenset(category.code for category in CATEGORY_INVENTORY if category.is_active)
_MAPPED_TARGETS: dict[tuple[str, str], tuple[str, ...]] = {
    (mapping.axis, mapping.source_code): mapping.target_codes
    for mapping in LEGACY_CROSSWALK
    if mapping.state == "mapped"
}


@dataclass(slots=True)
class ProjectionReport:
    """Counts of one mention projection run."""

    mentions_seen: int = 0
    mentions_projected: int = 0
    unknown_values: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ProjectedMention:
    """Canonical categories and direct confidence derived from one mention's legacy axes."""

    category_codes: tuple[str, ...]
    direct_category_confidence: float | None
    unknown_values: tuple[str, ...]


def project_axes(
    *,
    domain_codes: Sequence[str] | None,
    situation_codes: Sequence[str] | None,
    direct_domain_confidence: float | None,
    direct_situation_confidence: float | None,
) -> ProjectedMention:
    """Return the canonical categories of one mention's legacy axis values, deduplicated in order."""
    codes: list[str] = []
    unknown: list[str] = []
    for axis, values in (("domain", domain_codes or ()), ("life_situation", situation_codes or ())):
        for value in values:
            targets = _targets(axis, value)
            if targets:
                codes.extend(targets)
            else:
                unknown.append(value)
    direct = _strongest((direct_domain_confidence, direct_situation_confidence))
    return ProjectedMention(tuple(dict.fromkeys(codes)), direct, tuple(dict.fromkeys(unknown)))


def project_mention_categories(connection: Connection) -> ProjectionReport:
    """Write canonical categories to every mention that still carries legacy axis values."""
    report = ProjectionReport()
    for row in _legacy_rows(connection):
        report.mentions_seen += 1
        projected = project_axes(
            domain_codes=row.domain_codes,
            situation_codes=row.situation_codes,
            direct_domain_confidence=row.direct_domain_confidence,
            direct_situation_confidence=row.direct_situation_confidence,
        )
        report.unknown_values.extend(projected.unknown_values)
        _write(connection, row.id, projected)
        report.mentions_projected += 1
    return report


def _targets(axis: str, value: str) -> tuple[str, ...]:
    if value in ACTIVE_CATEGORY_CODES:
        return (value,)
    return _MAPPED_TARGETS.get((axis, value), ())


def _strongest(values: Iterable[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    return max(present, default=None)


def _legacy_rows(connection: Connection) -> list[sa.Row]:
    stmt = sa.select(
        MENTION_TABLE.c.id,
        MENTION_TABLE.c.domain_codes,
        MENTION_TABLE.c.situation_codes,
        MENTION_TABLE.c.direct_domain_confidence,
        MENTION_TABLE.c.direct_situation_confidence,
    ).where(
        sa.or_(
            MENTION_TABLE.c.domain_codes.is_not(None),
            MENTION_TABLE.c.situation_codes.is_not(None),
            MENTION_TABLE.c.direct_domain_confidence.is_not(None),
            MENTION_TABLE.c.direct_situation_confidence.is_not(None),
        )
    )
    return list(connection.execute(stmt).all())


def _write(connection: Connection, mention_id: object, projected: ProjectedMention) -> None:
    connection.execute(
        MENTION_TABLE.update()
        .where(MENTION_TABLE.c.id == mention_id)
        .values(
            category_codes=list(projected.category_codes) or None,
            direct_category_confidence=projected.direct_category_confidence,
        )
    )
