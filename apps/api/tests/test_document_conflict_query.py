"""Database-level behaviour of DocumentPromotion.find_conflicts (B7 characterisation and query shape)."""

from __future__ import annotations

import uuid
from collections.abc import Generator
from contextlib import contextmanager

import pytest
from app.features.documents.promotion import DocumentPromotion
from app.features.documents.repository import DocumentRepository
from app.features.taxonomy.repository import TaxonomyRepository
from app.features.taxonomy.service import TaxonomyService
from app.models.document import Document
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.url_normalization import normalize_url
from sqlalchemy import event
from sqlalchemy.orm import Session


@pytest.fixture
def jurisdiction(db_session: Session) -> Jurisdiction:
    row = Jurisdiction(kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Testland"}, code=f"T{uuid.uuid4().hex[:8]}")
    db_session.add(row)
    db_session.flush()
    return row


def _promotion(db_session: Session) -> DocumentPromotion:
    return DocumentPromotion(DocumentRepository(db_session), TaxonomyService(TaxonomyRepository(db_session)))


def _document(db_session: Session, jurisdiction: Jurisdiction, slug: str, official_url: str | None = None) -> Document:
    row = Document(jurisdiction_id=jurisdiction.id, slug=slug, title_i18n={"en": slug}, official_url=official_url)
    db_session.add(row)
    db_session.flush()
    return row


def _find(db_session: Session, jurisdiction: Jurisdiction, slug: str, official_url: str | None) -> list[uuid.UUID]:
    normalized = None if official_url is None else normalize_url(official_url)
    return _promotion(db_session).find_conflicts(jurisdiction_id=jurisdiction.id, slug=slug, normalized_url=normalized)


@contextmanager
def _count_statements(db_session: Session) -> Generator[list[str], None, None]:
    statements: list[str] = []
    connection = db_session.connection()

    def _before_cursor_execute(_conn: object, _cursor: object, statement: str, *_args: object) -> None:
        statements.append(statement)

    event.listen(connection, "before_cursor_execute", _before_cursor_execute)
    try:
        yield statements
    finally:
        event.remove(connection, "before_cursor_execute", _before_cursor_execute)


def test_conflict_on_same_slug(db_session: Session, jurisdiction: Jurisdiction) -> None:
    existing = _document(db_session, jurisdiction, "residency-permit", "https://example.gov/other")

    assert _find(db_session, jurisdiction, "residency-permit", "https://example.gov/x") == [existing.id]


def test_conflict_on_same_normalized_url_with_tracking_params_and_trailing_slash(
    db_session: Session, jurisdiction: Jurisdiction
) -> None:
    existing = _document(db_session, jurisdiction, "other-slug", "https://Example.gov/residency/?utm_source=x&b=2&a=1")

    assert _find(db_session, jurisdiction, "unrelated-slug", "https://example.gov/residency?a=1&b=2") == [existing.id]


def test_conflict_on_both_slug_and_url_returns_the_document_once(
    db_session: Session, jurisdiction: Jurisdiction
) -> None:
    existing = _document(db_session, jurisdiction, "residency-permit", "https://example.gov/residency")

    assert _find(db_session, jurisdiction, "residency-permit", "https://example.gov/residency/") == [existing.id]


def test_no_conflict_for_other_jurisdiction(db_session: Session, jurisdiction: Jurisdiction) -> None:
    other = Jurisdiction(kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Otherland"}, code=f"O{uuid.uuid4().hex[:8]}")
    db_session.add(other)
    db_session.flush()
    _document(db_session, other, "residency-permit", "https://example.gov/residency")

    assert _find(db_session, jurisdiction, "residency-permit", "https://example.gov/residency") == []


def test_url_less_candidate_matches_on_slug_only(db_session: Session, jurisdiction: Jurisdiction) -> None:
    same_slug = _document(db_session, jurisdiction, "residency-permit", None)
    _document(db_session, jurisdiction, "other-slug", "https://example.gov/residency")

    assert _find(db_session, jurisdiction, "residency-permit", None) == [same_slug.id]


def test_document_without_url_never_matches_a_url(db_session: Session, jurisdiction: Jurisdiction) -> None:
    _document(db_session, jurisdiction, "other-slug", None)

    assert _find(db_session, jurisdiction, "unrelated-slug", "https://example.gov/residency") == []


def test_different_query_values_do_not_conflict(db_session: Session, jurisdiction: Jurisdiction) -> None:
    _document(db_session, jurisdiction, "other-slug", "https://example.gov/residency?id=1")

    assert _find(db_session, jurisdiction, "unrelated-slug", "https://example.gov/residency?id=2") == []


def test_find_conflicts_fetches_only_matching_ids_in_one_select(
    db_session: Session, jurisdiction: Jurisdiction
) -> None:
    _document(db_session, jurisdiction, "residency-permit", "https://example.gov/residency")
    _document(db_session, jurisdiction, "other-slug", "https://example.gov/other")

    with _count_statements(db_session) as statements:
        _find(db_session, jurisdiction, "residency-permit", "https://example.gov/x")

    assert len(statements) == 1
    assert statements[0].lstrip().upper().startswith("SELECT")
    assert "slug" in statements[0]
    assert "normalized_url" in statements[0]
    assert "WHERE" in statements[0].upper()
