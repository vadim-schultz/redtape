"""Category backfill replay tests over the frozen legacy tables.

The replay reads the retired shapes declared in ``scripts.seed_data.legacy_tables`` and writes canonical links. Each
test creates those legacy tables inside its own rolled-back transaction, so the replay has its source schema without
any retired ORM model.
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from uuid import UUID

import pytest
import sqlalchemy as sa
from app.models.document import Document
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.taxonomy import Category, DocumentExternalClassification, document_category
from scripts.category_backfill import run_category_backfill
from scripts.seed_data.legacy_tables import (
    DOCUMENT_DOMAIN,
    DOCUMENT_LIFE_SITUATION,
    DOMAIN,
    LEGACY_METADATA,
    LIFE_SITUATION,
)
from scripts.seed_data.taxonomy import CATEGORY_CONTRACT_VERSION, LEGACY_CROSSWALK, term_id
from scripts.seed_taxonomy import seed_canonical_taxonomy
from sqlalchemy.orm import Session


@pytest.fixture
def legacy_session(db_session: Session) -> Session:
    """Create the retired legacy tables inside this test's transaction and return its session."""
    LEGACY_METADATA.create_all(
        db_session.connection(),
        tables=[DOMAIN, LIFE_SITUATION, DOCUMENT_DOMAIN, DOCUMENT_LIFE_SITUATION],
    )
    return db_session


def _document(session: Session) -> Document:
    country = Jurisdiction(
        kind=JurisdictionKind.COUNTRY,
        code=f"T{uuid.uuid4().hex[:8]}",
        name_i18n={"en": "Testland"},
    )
    session.add(country)
    session.flush()
    document = Document(
        jurisdiction_id=country.id,
        slug=f"doc-{uuid.uuid4().hex[:8]}",
        title_i18n={"en": "A document"},
    )
    session.add(document)
    session.flush()
    return document


def _legacy_domain(session: Session, document: Document, code: str, confidence: float) -> None:
    domain_id = uuid.uuid4()
    session.execute(DOMAIN.insert().values(id=domain_id, code=code))
    session.execute(
        DOCUMENT_DOMAIN.insert().values(document_id=document.id, domain_id=domain_id, confidence=confidence)
    )


def _legacy_situation(
    session: Session,
    document: Document,
    code: str,
    confidence: float,
    pvog_leaf_code: str | None = None,
) -> None:
    situation_id = uuid.uuid4()
    session.execute(LIFE_SITUATION.insert().values(id=situation_id, code=code))
    session.execute(
        DOCUMENT_LIFE_SITUATION.insert().values(
            document_id=document.id,
            life_situation_id=situation_id,
            confidence=confidence,
            pvog_leaf_code=pvog_leaf_code,
        )
    )


def _promotion_link(session: Session, document: Document, category_code: str, confidence: float) -> None:
    session.execute(
        document_category.insert().values(
            document_id=document.id,
            category_id=term_id(category_code),
            confidence=confidence,
            source="promotion",
            provenance={"source": "category_code_promotion"},
        )
    )


def _links(session: Session, document_id: UUID) -> dict[str, tuple[str, dict[str, object], float]]:
    """Return ``{category_code: (source, provenance, confidence)}`` for one document."""
    rows = session.execute(
        sa.select(
            Category.code,
            document_category.c.source,
            document_category.c.provenance,
            document_category.c.confidence,
        )
        .join(document_category, document_category.c.category_id == Category.id)
        .where(document_category.c.document_id == document_id)
    ).all()
    return {code: (source, provenance, confidence) for code, source, provenance, confidence in rows}


def test_backfill_maps_old_links_to_canonical_links_with_confidence(legacy_session: Session) -> None:
    """Backfill · map both legacy axes to canonical links using the maximum score."""
    document = _document(legacy_session)
    _legacy_domain(legacy_session, document, "housing", 0.72)
    _legacy_situation(legacy_session, document, "moving-house", 0.91)

    report = run_category_backfill(legacy_session)
    legacy_session.flush()

    rows = legacy_session.execute(
        sa.select(Category.code, document_category.c.confidence)
        .join(document_category, document_category.c.category_id == Category.id)
        .where(document_category.c.document_id == document.id)
        .order_by(Category.code)
    ).all()

    assert rows == [("home-and-housing", 0.72), ("moving-house", 0.91)]
    assert report.category_links_created == 2


def test_backfill_preserves_pvog_external_classifications(legacy_session: Session) -> None:
    """Backfill · preserve the raw PVOG leaf independently of the category link."""
    document = _document(legacy_session)
    _legacy_domain(legacy_session, document, "housing", 0.8)
    _legacy_situation(legacy_session, document, "moving-house", 0.8, pvog_leaf_code="1050200")

    report = run_category_backfill(legacy_session)
    legacy_session.flush()

    classification = legacy_session.execute(
        sa.select(DocumentExternalClassification).where(
            DocumentExternalClassification.document_id == document.id,
        )
    ).scalar_one()

    assert classification.source == "pvog"
    assert classification.external_code == "1050200"
    assert classification.external_level == "leaf"
    assert report.external_classifications_created == 1


def test_backfill_ambiguous_mapping_is_reported_without_silent_link_loss(legacy_session: Session) -> None:
    """Backfill · report manual-review mappings while retaining the legacy projection."""
    document = _document(legacy_session)
    _legacy_domain(legacy_session, document, "housing", 0.8)
    ambiguous = replace(
        next(mapping for mapping in LEGACY_CROSSWALK if mapping.axis == "domain" and mapping.source_code == "housing"),
        state="manual_review",
        target_codes=(),
    )
    crosswalk = tuple(
        ambiguous if mapping.source_code == "housing" and mapping.axis == "domain" else mapping
        for mapping in LEGACY_CROSSWALK
    )

    report = run_category_backfill(legacy_session, crosswalk=crosswalk)
    legacy_session.flush()

    assert report.ambiguous_rows == 1
    assert (
        legacy_session.execute(
            sa.select(sa.func.count()).select_from(DOCUMENT_DOMAIN).where(DOCUMENT_DOMAIN.c.document_id == document.id)
        ).scalar_one()
        == 1
    )
    assert (
        legacy_session.execute(
            sa.select(sa.func.count())
            .select_from(document_category)
            .where(document_category.c.document_id == document.id)
        ).scalar_one()
        == 0
    )


def test_backfill_rerun_does_not_duplicate_links_or_classifications(legacy_session: Session) -> None:
    """Backfill · rerun updates the projection in place without duplicate rows."""
    document = _document(legacy_session)
    _legacy_domain(legacy_session, document, "housing", 0.7)
    _legacy_situation(legacy_session, document, "moving-house", 0.7, pvog_leaf_code="1050200")

    run_category_backfill(legacy_session)
    first_counts = (
        legacy_session.execute(
            sa.select(sa.func.count())
            .select_from(document_category)
            .where(document_category.c.document_id == document.id)
        ).scalar_one(),
        legacy_session.execute(
            sa.select(sa.func.count())
            .select_from(DocumentExternalClassification)
            .where(DocumentExternalClassification.document_id == document.id)
        ).scalar_one(),
    )

    rerun = run_category_backfill(legacy_session)
    legacy_session.flush()

    assert (
        legacy_session.execute(
            sa.select(sa.func.count())
            .select_from(document_category)
            .where(document_category.c.document_id == document.id)
        ).scalar_one(),
        legacy_session.execute(
            sa.select(sa.func.count())
            .select_from(DocumentExternalClassification)
            .where(DocumentExternalClassification.document_id == document.id)
        ).scalar_one(),
    ) == first_counts
    assert rerun.category_links_created == 0
    assert rerun.external_classifications_created == 0


def test_backfill_dry_run_reports_without_writing(legacy_session: Session) -> None:
    """Backfill · dry-run reports planned legacy rows without changing target tables."""
    document = _document(legacy_session)
    _legacy_domain(legacy_session, document, "housing", 0.8)

    report = run_category_backfill(legacy_session, dry_run=True)
    legacy_session.flush()

    assert report.dry_run is True
    assert report.legacy_rows == 1
    assert legacy_session.execute(sa.select(sa.func.count()).select_from(document_category)).scalar_one() == 0
    assert legacy_session.execute(sa.select(sa.func.count()).select_from(Category)).scalar_one() == 0


@pytest.mark.parametrize(
    ("stored_confidence", "expected_confidence"),
    [(0.9, 0.9), (0.3, 0.6)],
    ids=["stored-is-higher", "projection-is-higher"],
)
def test_replay_keeps_promotion_source_and_provenance(
    legacy_session: Session,
    stored_confidence: float,
    expected_confidence: float,
) -> None:
    """Replay · a promotion-written link keeps its source and provenance and takes the higher confidence."""
    document = _document(legacy_session)
    seed_canonical_taxonomy(legacy_session)
    _promotion_link(legacy_session, document, "home-and-housing", stored_confidence)
    _legacy_domain(legacy_session, document, "housing", 0.6)
    _legacy_situation(legacy_session, document, "moving-house", 0.8)

    run_category_backfill(legacy_session)
    legacy_session.flush()

    links = _links(legacy_session, document.id)
    assert links["home-and-housing"] == (
        "promotion",
        {"source": "category_code_promotion"},
        expected_confidence,
    )
    assert links["moving-house"] == (
        "legacy_crosswalk",
        {
            "artifact_version": CATEGORY_CONTRACT_VERSION,
            "legacy_axes": ["life_situation"],
            "score_combination": "max",
        },
        0.8,
    )


def test_replay_conflicting_crosswalk_writes_no_row_and_counts_conflict(legacy_session: Session) -> None:
    """Replay · a duplicated crosswalk entry writes no link for its pair, counts the conflict, and a rerun adds nothing."""
    document = _document(legacy_session)
    _legacy_domain(legacy_session, document, "housing", 0.6)
    duplicate = next(
        mapping for mapping in LEGACY_CROSSWALK if mapping.axis == "domain" and mapping.source_code == "housing"
    )
    crosswalk = (*LEGACY_CROSSWALK, duplicate)

    report = run_category_backfill(legacy_session, crosswalk=crosswalk)
    legacy_session.flush()

    assert report.conflict_rows == 1
    assert _links(legacy_session, document.id) == {}

    rerun = run_category_backfill(legacy_session, crosswalk=crosswalk)
    legacy_session.flush()

    assert _links(legacy_session, document.id) == {}
    assert rerun.category_links_created == 0
    assert rerun.category_links_updated == 0
