"""Backfill canonical category links from the frozen legacy crosswalk."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from typing import Literal
from uuid import UUID

import sqlalchemy as sa
from app.db import SessionLocal
from app.models.taxonomy import DocumentExternalClassification, document_category
from sqlalchemy.orm import Session

from scripts.seed_data.legacy_tables import DOCUMENT_DOMAIN, DOCUMENT_LIFE_SITUATION, DOMAIN, LIFE_SITUATION
from scripts.seed_data.taxonomy import (
    CATEGORY_CONTRACT_VERSION,
    CATEGORY_INVENTORY,
    LEGACY_CROSSWALK,
    PVOG_SOURCE_VERSION,
    LegacyMapping,
    term_id,
)
from scripts.seed_taxonomy import seed_canonical_taxonomy

LegacyAxisName = Literal["domain", "life_situation"]


@dataclass(frozen=True, slots=True)
class BackfillIssue:
    """One legacy row that needs operator attention."""

    document_id: UUID
    axis: LegacyAxisName
    source_code: str
    reason: str


@dataclass(slots=True)
class BackfillReport:
    """Counts and conflicts produced by one category backfill run."""

    dry_run: bool
    category_rows: int
    legacy_rows: int
    category_links_created: int = 0
    category_links_updated: int = 0
    external_classifications_created: int = 0
    external_classifications_seen: int = 0
    unmapped_rows: int = 0
    ambiguous_rows: int = 0
    conflict_rows: int = 0
    null_confidence_rows: int = 0
    issues: list[BackfillIssue] = field(default_factory=list)


@dataclass(slots=True)
class _LinkProjection:
    """One accumulated document/category projection."""

    document_id: UUID
    category_id: UUID
    confidence: float
    axes: set[str]


@dataclass(frozen=True, slots=True)
class _LegacyRow:
    """One persisted legacy link read for transformation."""

    document_id: UUID
    axis: LegacyAxisName
    source_code: str
    confidence: float | None


@dataclass(slots=True)
class _ProjectionContext:
    """State shared while transforming legacy rows."""

    active_codes: set[str]
    projections: dict[tuple[UUID, UUID], _LinkProjection]
    report: BackfillReport


@dataclass(frozen=True, slots=True)
class _CrosswalkIndex:
    """Crosswalk lookup plus duplicate keys that must not be applied."""

    mappings: dict[tuple[str, str], LegacyMapping]
    duplicates: frozenset[tuple[str, str]]


def _mapping_index(crosswalk: tuple[LegacyMapping, ...]) -> _CrosswalkIndex:
    """Index crosswalk entries while retaining conflicting duplicate keys."""
    grouped: dict[tuple[str, str], list[LegacyMapping]] = {}
    for mapping in crosswalk:
        grouped.setdefault((mapping.axis, mapping.source_code), []).append(mapping)
    return _CrosswalkIndex(
        mappings={key: rows[0] for key, rows in grouped.items() if len(rows) == 1},
        duplicates=frozenset(key for key, rows in grouped.items() if len(rows) > 1),
    )


def _legacy_rows(
    session: Session,
    *,
    axis: LegacyAxisName,
) -> list[_LegacyRow]:
    """Read one legacy axis with its persisted confidence."""
    if axis == "domain":
        stmt = sa.select(DOCUMENT_DOMAIN.c.document_id, DOMAIN.c.code, DOCUMENT_DOMAIN.c.confidence).join(
            DOMAIN, DOMAIN.c.id == DOCUMENT_DOMAIN.c.domain_id
        )
    else:
        stmt = sa.select(
            DOCUMENT_LIFE_SITUATION.c.document_id,
            LIFE_SITUATION.c.code,
            DOCUMENT_LIFE_SITUATION.c.confidence,
        ).join(LIFE_SITUATION, LIFE_SITUATION.c.id == DOCUMENT_LIFE_SITUATION.c.life_situation_id)
    return [
        _LegacyRow(document_id, axis, source_code, confidence)
        for document_id, source_code, confidence in session.execute(stmt).tuples().all()
    ]


def _confidence(value: float | None, report: BackfillReport) -> float:
    """Return a database-safe confidence while recording legacy nulls."""
    if value is None:
        report.null_confidence_rows += 1
        return 1.0
    return float(value)


def _add_projection(
    projections: dict[tuple[UUID, UUID], _LinkProjection],
    *,
    document_id: UUID,
    category_id: UUID,
    confidence: float,
    axis: LegacyAxisName,
) -> None:
    """Combine multiple old-axis links into one canonical link using the approved maximum."""
    key = (document_id, category_id)
    existing = projections.get(key)
    if existing is None:
        projections[key] = _LinkProjection(document_id, category_id, confidence, {axis})
        return
    existing.confidence = max(existing.confidence, confidence)
    existing.axes.add(axis)


def _project_legacy_row(row: _LegacyRow, mapping: LegacyMapping | None, context: _ProjectionContext) -> None:
    """Apply one crosswalk row or record why it cannot be projected."""
    if mapping is None:
        context.report.unmapped_rows += 1
        context.report.issues.append(
            BackfillIssue(row.document_id, row.axis, row.source_code, "crosswalk entry is missing")
        )
        return
    if mapping.state != "mapped":
        context.report.ambiguous_rows += 1
        context.report.issues.append(
            BackfillIssue(row.document_id, row.axis, row.source_code, f"crosswalk state is {mapping.state}")
        )
        return
    unknown_targets = [code for code in mapping.target_codes if code not in context.active_codes]
    if unknown_targets:
        context.report.conflict_rows += 1
        context.report.issues.append(
            BackfillIssue(
                row.document_id,
                row.axis,
                row.source_code,
                f"unknown target(s): {', '.join(unknown_targets)}",
            )
        )
        return
    confidence = _confidence(row.confidence, context.report)
    for category_code in mapping.target_codes:
        _add_projection(
            context.projections,
            document_id=row.document_id,
            category_id=term_id(category_code),
            confidence=confidence,
            axis=row.axis,
        )


def _collect_projections(
    session: Session,
    *,
    crosswalk: tuple[LegacyMapping, ...],
    report: BackfillReport,
) -> dict[tuple[UUID, UUID], _LinkProjection]:
    """Transform legacy links into canonical projections and operator issues."""
    crosswalk_index = _mapping_index(crosswalk)
    context = _ProjectionContext(
        active_codes={category.code for category in CATEGORY_INVENTORY if category.is_active},
        projections={},
        report=report,
    )

    for axis in ("domain", "life_situation"):
        rows = _legacy_rows(session, axis=axis)
        report.legacy_rows += len(rows)
        for row in rows:
            if (row.axis, row.source_code) in crosswalk_index.duplicates:
                report.conflict_rows += 1
                report.issues.append(
                    BackfillIssue(row.document_id, row.axis, row.source_code, "crosswalk entry is duplicated")
                )
                continue
            _project_legacy_row(
                row,
                mapping=crosswalk_index.mappings.get((row.axis, row.source_code)),
                context=context,
            )
    return context.projections


def _external_classification_keys(session: Session) -> set[tuple[UUID, str]]:
    """Read distinct PVOG leaf facts from the legacy situation links."""
    stmt = sa.select(DOCUMENT_LIFE_SITUATION.c.document_id, DOCUMENT_LIFE_SITUATION.c.pvog_leaf_code).where(
        DOCUMENT_LIFE_SITUATION.c.pvog_leaf_code.is_not(None)
    )
    return {(document_id, leaf_code) for document_id, leaf_code in session.execute(stmt).tuples().all()}


def _persist_links(
    session: Session, projections: dict[tuple[UUID, UUID], _LinkProjection], report: BackfillReport
) -> None:
    """Upsert canonical document links without deleting any target or legacy link."""
    existing = {
        (document_id, category_id): (confidence, source, provenance)
        for document_id, category_id, confidence, source, provenance in session.execute(
            sa.select(
                document_category.c.document_id,
                document_category.c.category_id,
                document_category.c.confidence,
                document_category.c.source,
                document_category.c.provenance,
            )
        ).tuples()
    }
    for key, projection in projections.items():
        provenance = {
            "artifact_version": CATEGORY_CONTRACT_VERSION,
            "legacy_axes": sorted(projection.axes),
            "score_combination": "max",
        }
        previous = existing.get(key)
        values = {
            "confidence": projection.confidence,
            "source": "legacy_crosswalk",
            "provenance": provenance,
        }
        if previous is None:
            session.execute(document_category.insert().values(document_id=key[0], category_id=key[1], **values))
            report.category_links_created += 1
            continue
        if previous != (projection.confidence, "legacy_crosswalk", provenance):
            session.execute(
                document_category.update()
                .where(
                    document_category.c.document_id == key[0],
                    document_category.c.category_id == key[1],
                )
                .values(**values)
            )
            report.category_links_updated += 1


def _persist_external_classifications(session: Session, keys: set[tuple[UUID, str]], report: BackfillReport) -> None:
    """Insert raw PVOG leaf facts once, preserving them separately from category links."""
    report.external_classifications_seen = len(keys)
    existing = {
        (document_id, external_code)
        for document_id, external_code in session.execute(
            sa.select(
                DocumentExternalClassification.document_id,
                DocumentExternalClassification.external_code,
            ).where(
                DocumentExternalClassification.source == "pvog",
                DocumentExternalClassification.external_level == "leaf",
                DocumentExternalClassification.source_version == PVOG_SOURCE_VERSION,
            )
        ).tuples()
    }
    for document_id, external_code in sorted(keys, key=lambda item: (str(item[0]), item[1])):
        if (document_id, external_code) in existing:
            continue
        session.add(
            DocumentExternalClassification(
                document_id=document_id,
                source="pvog",
                external_level="leaf",
                external_code=external_code,
                source_version=PVOG_SOURCE_VERSION,
            )
        )
        report.external_classifications_created += 1


def run_category_backfill(
    session: Session,
    *,
    dry_run: bool = False,
    crosswalk: tuple[LegacyMapping, ...] = LEGACY_CROSSWALK,
) -> BackfillReport:
    """Seed the canonical inventory and backfill links and PVOG facts idempotently."""
    report = BackfillReport(dry_run=dry_run, category_rows=len(CATEGORY_INVENTORY), legacy_rows=0)
    projections = _collect_projections(session, crosswalk=crosswalk, report=report)
    external_keys = _external_classification_keys(session)
    report.external_classifications_seen = len(external_keys)
    if dry_run:
        return report

    seed_canonical_taxonomy(session)
    _persist_links(session, projections, report)
    _persist_external_classifications(session, external_keys, report)
    session.flush()
    return report


def _parser() -> argparse.ArgumentParser:
    """Build the operator command parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="report planned changes without writing rows")
    return parser


def main() -> None:
    """Run the backfill in one transaction and print a JSON report."""
    args = _parser().parse_args()
    with SessionLocal() as session:
        report = run_category_backfill(session, dry_run=args.dry_run)
        if not args.dry_run:
            session.commit()
    print(json.dumps(asdict(report), default=str, sort_keys=True))


if __name__ == "__main__":
    main()
