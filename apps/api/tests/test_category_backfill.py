from __future__ import annotations

import uuid
from dataclasses import replace

import sqlalchemy as sa
from app.models.document import Document
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.taxonomy import (
    Category,
    DocumentExternalClassification,
    Domain,
    LifeSituation,
    document_category,
    document_domain,
    document_life_situation,
)
from scripts.category_backfill import run_category_backfill
from scripts.seed_data.taxonomy import LEGACY_CROSSWALK
from sqlalchemy.orm import Session


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


def _old_terms(session: Session) -> tuple[Domain, LifeSituation]:
    domain = Domain(code="housing", name_i18n={"en": "Housing"})
    situation = LifeSituation(code="moving-house", name_i18n={"en": "Moving house"})
    session.add_all([domain, situation])
    session.flush()
    return domain, situation


def test_backfill_maps_old_links_to_canonical_links_with_confidence(db_session: Session) -> None:
    """Backfill · map both legacy axes to canonical links using the maximum score."""
    document = _document(db_session)
    domain, situation = _old_terms(db_session)
    db_session.execute(document_domain.insert().values(document_id=document.id, domain_id=domain.id, confidence=0.72))
    db_session.execute(
        document_life_situation.insert().values(
            document_id=document.id, life_situation_id=situation.id, confidence=0.91
        )
    )

    report = run_category_backfill(db_session)
    db_session.flush()

    rows = db_session.execute(
        sa.select(Category.code, document_category.c.confidence)
        .join(document_category, document_category.c.category_id == Category.id)
        .where(document_category.c.document_id == document.id)
        .order_by(Category.code)
    ).all()

    assert rows == [("home-and-housing", 0.72), ("moving-house", 0.91)]
    assert report.category_links_created == 2


def test_backfill_preserves_pvog_external_classifications(db_session: Session) -> None:
    """Backfill · preserve the raw PVOG leaf independently of the category link."""
    document = _document(db_session)
    domain, situation = _old_terms(db_session)
    db_session.execute(document_domain.insert().values(document_id=document.id, domain_id=domain.id, confidence=0.8))
    db_session.execute(
        document_life_situation.insert().values(
            document_id=document.id,
            life_situation_id=situation.id,
            confidence=0.8,
            pvog_leaf_code="1050200",
        )
    )

    report = run_category_backfill(db_session)
    db_session.flush()

    classification = db_session.execute(
        sa.select(DocumentExternalClassification).where(
            DocumentExternalClassification.document_id == document.id,
        )
    ).scalar_one()

    assert classification.source == "pvog"
    assert classification.external_code == "1050200"
    assert classification.external_level == "leaf"
    assert report.external_classifications_created == 1


def test_backfill_ambiguous_mapping_is_reported_without_silent_link_loss(db_session: Session) -> None:
    """Backfill · report manual-review mappings while retaining the legacy projection."""
    document = _document(db_session)
    domain, _ = _old_terms(db_session)
    db_session.execute(document_domain.insert().values(document_id=document.id, domain_id=domain.id, confidence=0.8))
    ambiguous = replace(
        next(mapping for mapping in LEGACY_CROSSWALK if mapping.axis == "domain" and mapping.source_code == "housing"),
        state="manual_review",
        target_codes=(),
    )
    crosswalk = tuple(
        ambiguous if mapping.source_code == "housing" and mapping.axis == "domain" else mapping
        for mapping in LEGACY_CROSSWALK
    )

    report = run_category_backfill(db_session, crosswalk=crosswalk)
    db_session.flush()

    assert report.ambiguous_rows == 1
    assert (
        db_session.execute(
            sa.select(sa.func.count()).select_from(document_domain).where(document_domain.c.document_id == document.id)
        ).scalar_one()
        == 1
    )
    assert (
        db_session.execute(
            sa.select(sa.func.count())
            .select_from(document_category)
            .where(document_category.c.document_id == document.id)
        ).scalar_one()
        == 0
    )


def test_backfill_rerun_does_not_duplicate_links_or_classifications(db_session: Session) -> None:
    """Backfill · rerun updates the projection in place without duplicate rows."""
    document = _document(db_session)
    domain, situation = _old_terms(db_session)
    db_session.execute(document_domain.insert().values(document_id=document.id, domain_id=domain.id, confidence=0.7))
    db_session.execute(
        document_life_situation.insert().values(
            document_id=document.id,
            life_situation_id=situation.id,
            confidence=0.7,
            pvog_leaf_code="1050200",
        )
    )

    run_category_backfill(db_session)
    first_counts = (
        db_session.execute(
            sa.select(sa.func.count())
            .select_from(document_category)
            .where(document_category.c.document_id == document.id)
        ).scalar_one(),
        db_session.execute(
            sa.select(sa.func.count())
            .select_from(DocumentExternalClassification)
            .where(DocumentExternalClassification.document_id == document.id)
        ).scalar_one(),
    )

    rerun = run_category_backfill(db_session)
    db_session.flush()

    assert (
        db_session.execute(
            sa.select(sa.func.count())
            .select_from(document_category)
            .where(document_category.c.document_id == document.id)
        ).scalar_one(),
        db_session.execute(
            sa.select(sa.func.count())
            .select_from(DocumentExternalClassification)
            .where(DocumentExternalClassification.document_id == document.id)
        ).scalar_one(),
    ) == first_counts
    assert rerun.category_links_created == 0
    assert rerun.external_classifications_created == 0


def test_backfill_dry_run_reports_without_writing(db_session: Session) -> None:
    """Backfill · dry-run reports planned legacy rows without changing target tables."""
    document = _document(db_session)
    domain, _ = _old_terms(db_session)
    db_session.execute(document_domain.insert().values(document_id=document.id, domain_id=domain.id, confidence=0.8))

    report = run_category_backfill(db_session, dry_run=True)
    db_session.flush()

    assert report.dry_run is True
    assert report.legacy_rows == 1
    assert db_session.execute(sa.select(sa.func.count()).select_from(document_category)).scalar_one() == 0
    assert db_session.execute(sa.select(sa.func.count()).select_from(Category)).scalar_one() == 0
