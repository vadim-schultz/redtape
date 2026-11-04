"""Document.normalized_url is kept in step with official_url by the model (B7)."""

from __future__ import annotations

import uuid

import pytest
from app.models.document import Document
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.url_normalization import normalize_url
from sqlalchemy import select
from sqlalchemy.orm import Session


@pytest.fixture
def jurisdiction(db_session: Session) -> Jurisdiction:
    row = Jurisdiction(kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Testland"}, code=f"T{uuid.uuid4().hex[:8]}")
    db_session.add(row)
    db_session.flush()
    return row


def test_document_sets_normalized_url_from_official_url(db_session: Session, jurisdiction: Jurisdiction) -> None:
    document = Document(
        jurisdiction_id=jurisdiction.id,
        slug="residency-permit",
        official_url="https://Example.gov/residency/?utm_source=x&b=2&a=1#top",
    )
    db_session.add(document)
    db_session.flush()

    assert document.normalized_url == normalize_url("https://Example.gov/residency/?utm_source=x&b=2&a=1#top")
    assert document.normalized_url == "https://example.gov/residency?a=1&b=2"


def test_reassigning_official_url_updates_normalized_url(db_session: Session, jurisdiction: Jurisdiction) -> None:
    document = Document(jurisdiction_id=jurisdiction.id, slug="residency-permit", official_url="https://example.gov/a/")

    document.official_url = "https://example.gov/b"

    assert document.normalized_url == "https://example.gov/b"


def test_clearing_official_url_clears_normalized_url(db_session: Session, jurisdiction: Jurisdiction) -> None:
    document = Document(jurisdiction_id=jurisdiction.id, slug="residency-permit", official_url="https://example.gov/a")
    db_session.add(document)
    db_session.flush()

    document.official_url = None
    db_session.flush()

    assert document.normalized_url is None
    stored = db_session.execute(select(Document.normalized_url).where(Document.id == document.id)).scalar_one()
    assert stored is None


def test_document_without_official_url_has_no_normalized_url(db_session: Session, jurisdiction: Jurisdiction) -> None:
    document = Document(jurisdiction_id=jurisdiction.id, slug="residency-permit")

    assert document.normalized_url is None


def test_normalized_url_fits_the_column_for_a_500_char_url_whose_query_expands_on_reencoding(
    db_session: Session, jurisdiction: Jurisdiction
) -> None:
    # Each "ä" is one character in official_url but "%C3%A4" (six characters) once re-encoded by normalize_url.
    # 100 of them expand the 500-character URL to exactly 1000 characters, the column width.
    official_url = "https://example.gov/x?q=" + "ä" * 100 + "a" * (500 - len("https://example.gov/x?q=") - 100)
    assert len(official_url) == 500
    document = Document(jurisdiction_id=jurisdiction.id, slug="long-url", official_url=official_url)
    db_session.add(document)
    db_session.flush()

    stored = db_session.execute(select(Document.normalized_url).where(Document.id == document.id)).scalar_one()
    assert stored == normalize_url(official_url)
    assert len(stored) > len(official_url)
