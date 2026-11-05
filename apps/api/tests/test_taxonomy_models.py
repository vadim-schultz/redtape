from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from app.models.document import Document
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.taxonomy import (
    Category,
    CategoryExternalMapping,
    DocumentExternalClassification,
    document_category,
)
from scripts.seed_data.taxonomy import CATEGORY_INVENTORY, TaxonomyContractError, validate_category_inventory
from scripts.seed_taxonomy import seed_canonical_taxonomy
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def _document(session: Session) -> Document:
    country = Jurisdiction(
        kind=JurisdictionKind.COUNTRY,
        name_i18n={"en": "Testland"},
        code=f"T{uuid.uuid4().hex[:8]}",
    )
    session.add(country)
    session.flush()
    document = Document(jurisdiction_id=country.id, slug=f"doc-{uuid.uuid4().hex[:8]}")
    session.add(document)
    session.flush()
    return document


def _count(session: Session, table: sa.Table) -> int:
    return session.execute(sa.select(sa.func.count()).select_from(table)).scalar_one()


def test_category_persists_localized_names_and_external_mapping(db_session: Session) -> None:
    category = Category(code="test-home-and-housing", name_i18n={"de": "Wohnen", "en": "Housing"})
    db_session.add(category)
    db_session.flush()
    db_session.add(
        CategoryExternalMapping(
            category_id=category.id,
            source="pvog",
            external_level="parent",
            external_code="105",
            source_version="v7",
        )
    )
    db_session.flush()
    db_session.expire_all()

    stored = db_session.scalar(sa.select(Category).where(Category.code == "test-home-and-housing"))
    assert stored is not None
    assert stored.name_i18n == {"de": "Wohnen", "en": "Housing"}
    assert stored.external_mappings[0].external_code == "105"


def test_category_duplicate_code_is_rejected(db_session: Session) -> None:
    db_session.add(Category(code="housing", name_i18n={"en": "Housing"}))
    db_session.flush()
    db_session.add(Category(code="housing", name_i18n={"en": "Housing"}))

    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.parametrize("code", ["Umzüge", "moving house", "", "Housing", "-a", "a--b"])
def test_category_non_kebab_or_accented_code_is_rejected(db_session: Session, code: str) -> None:
    db_session.add(Category(code=code, name_i18n={"en": code}))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_document_category_link_defaults_confidence_and_provenance(db_session: Session) -> None:
    document = _document(db_session)
    category = Category(code="housing", name_i18n={"en": "Housing"})
    db_session.add(category)
    db_session.flush()
    db_session.execute(document_category.insert().values(document_id=document.id, category_id=category.id))

    confidence, source, provenance = db_session.execute(
        sa.select(document_category.c.confidence, document_category.c.source, document_category.c.provenance).where(
            document_category.c.document_id == document.id
        )
    ).one()

    assert confidence == 1.0
    assert source == "legacy_crosswalk"
    assert provenance == {}


def test_document_category_link_is_unique(db_session: Session) -> None:
    document = _document(db_session)
    category = Category(code="housing", name_i18n={"en": "Housing"})
    db_session.add(category)
    db_session.flush()
    link = document_category.insert().values(document_id=document.id, category_id=category.id)
    db_session.execute(link)

    with pytest.raises(IntegrityError):
        db_session.execute(link)


def test_deleting_a_document_removes_category_links_and_keeps_category(db_session: Session) -> None:
    document = _document(db_session)
    category = Category(code="housing", name_i18n={"en": "Housing"})
    document.categories.append(category)
    db_session.add(document)
    db_session.flush()

    db_session.execute(sa.delete(Document).where(Document.id == document.id))

    assert _count(db_session, document_category) == 0
    assert db_session.scalar(sa.select(Category).where(Category.id == category.id)) is not None


def test_external_classification_preserves_pvog_leaf_separately(db_session: Session) -> None:
    document = _document(db_session)
    db_session.add(
        DocumentExternalClassification(
            document_id=document.id,
            source="pvog",
            external_level="leaf",
            external_code="1050200",
            source_version="v7",
        )
    )
    db_session.flush()

    stored = db_session.scalar(sa.select(DocumentExternalClassification))
    assert stored is not None
    assert stored.external_code == "1050200"


def test_category_seeds_roots_and_children_with_stable_ids(db_session: Session) -> None:
    seed_canonical_taxonomy(db_session)
    db_session.flush()
    root = db_session.scalar(sa.select(Category).where(Category.code == "family-and-relationships"))
    child = db_session.scalar(sa.select(Category).where(Category.code == "birth-and-parenthood"))
    assert root is not None and child is not None
    root_id, child_id = root.id, child.id

    root.name_i18n = {"de": "Familie & Beziehungen", "en": "Family & relationships"}
    seed_canonical_taxonomy(db_session)
    db_session.flush()

    assert db_session.get(Category, root_id) is root
    assert db_session.get(Category, child_id) is child
    assert child.parent_id == root_id
    assert _count(db_session, Category.__table__) == len(CATEGORY_INVENTORY)


def test_category_duplicate_missing_parent_or_cycle_is_rejected() -> None:
    """Category inventory validation rejects invalid tree definitions."""
    from dataclasses import replace

    root = next(category for category in CATEGORY_INVENTORY if category.parent_code is None)
    child = next(category for category in CATEGORY_INVENTORY if category.parent_code == root.code)

    with pytest.raises(TaxonomyContractError, match="duplicate"):
        validate_category_inventory((*CATEGORY_INVENTORY, root))
    with pytest.raises(TaxonomyContractError, match="unknown parent"):
        validate_category_inventory(
            (
                replace(child, parent_code="missing-parent"),
                *(category for category in CATEGORY_INVENTORY if category.code != child.code),
            )
        )
    with pytest.raises(TaxonomyContractError, match="cycle"):
        validate_category_inventory(
            (
                replace(root, parent_code=child.code),
                replace(child, parent_code=root.code),
                *(category for category in CATEGORY_INVENTORY if category.code not in {root.code, child.code}),
            )
        )
