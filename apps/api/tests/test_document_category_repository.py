"""Persist canonical category links and their confidence."""

from __future__ import annotations

import uuid

import pytest
from app.features.documents.repository import DocumentRepository
from app.models.document import Document
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.taxonomy import Category, document_category
from sqlalchemy import select
from sqlalchemy.orm import Session


@pytest.fixture
def jurisdiction(db_session: Session) -> Jurisdiction:
    row = Jurisdiction(kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Testland"}, code=f"T{uuid.uuid4().hex[:8]}")
    db_session.add(row)
    db_session.flush()
    return row


def _repo(db_session: Session) -> DocumentRepository:
    return DocumentRepository(db_session)


def test_add_without_scores_links_nothing(db_session: Session, jurisdiction: Jurisdiction) -> None:
    document = _repo(db_session).add(
        Document(jurisdiction_id=jurisdiction.id, slug="no-tags"),
        category_scores={},
    )

    assert _repo(db_session).get_category_confidence(document.id) == {}


def test_add_writes_resolved_category_score_and_pvog_provenance(
    db_session: Session, jurisdiction: Jurisdiction
) -> None:
    db_session.add(Category(code="test-home-and-housing", name_i18n={"en": "Home & housing"}))
    db_session.flush()

    document = _repo(db_session).add(
        Document(jurisdiction_id=jurisdiction.id, slug="canonical-tagged"),
        category_scores={"test-home-and-housing": 0.84},
        pvog_leaf_codes={"test-home-and-housing": "1050200"},
    )

    row = db_session.execute(
        select(document_category.c.confidence, document_category.c.source, document_category.c.provenance).where(
            document_category.c.document_id == document.id
        )
    ).one()
    assert row[0] == pytest.approx(0.84)
    assert row[1] == "promotion"
    assert row[2] == {"source": "category_code_promotion", "pvog_leaf_code": "1050200"}


def test_add_rejects_an_unknown_category_code(db_session: Session, jurisdiction: Jurisdiction) -> None:
    with pytest.raises(ValueError, match="Unknown category code"):
        _repo(db_session).add(
            Document(jurisdiction_id=jurisdiction.id, slug="invalid-tag"),
            category_scores={"does-not-exist": 0.84},
        )


def test_list_page_orders_matching_categories_by_confidence(db_session: Session, jurisdiction: Jurisdiction) -> None:
    db_session.add(Category(code="test-home-and-housing", name_i18n={"en": "Home & housing"}))
    db_session.flush()
    repo = _repo(db_session)
    repo.add(
        Document(jurisdiction_id=jurisdiction.id, slug="low"),
        category_scores={"test-home-and-housing": 0.1},
    )
    repo.add(
        Document(jurisdiction_id=jurisdiction.id, slug="high"),
        category_scores={"test-home-and-housing": 0.9},
    )

    category_id = db_session.scalar(select(Category.id).where(Category.code == "test-home-and-housing"))
    assert category_id is not None
    rows = repo.list_page(jurisdiction_id=jurisdiction.id, offset=0, limit=10, category_ids=[category_id])

    assert [row.slug for row in rows] == ["high", "low"]


def test_list_page_without_category_filter_orders_by_slug(db_session: Session, jurisdiction: Jurisdiction) -> None:
    repo = _repo(db_session)
    repo.add(Document(jurisdiction_id=jurisdiction.id, slug="b"), category_scores={})
    repo.add(Document(jurisdiction_id=jurisdiction.id, slug="a"), category_scores={})

    rows = repo.list_page(jurisdiction_id=jurisdiction.id, offset=0, limit=10)

    assert [row.slug for row in rows] == ["a", "b"]
