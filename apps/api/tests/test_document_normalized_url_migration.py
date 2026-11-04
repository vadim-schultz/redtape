"""The normalized_url migration adds the column and index, backfills idempotently, and downgrades cleanly (B7)."""

from __future__ import annotations

import importlib.util
import uuid
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.url_normalization import normalize_url
from sqlalchemy.orm import Session

MIGRATION = Path(__file__).resolve().parent.parent / "alembic" / "versions" / "20261104_document_normalized_url.py"
INDEX_NAME = "ix_document_jurisdiction_normalized_url"

CORPUS = [
    "https://example.gov/residency",
    "https://Example.GOV/residency/",
    "https://example.gov/residency/?utm_source=newsletter&b=2&a=1",
    "https://example.gov/residency?fbclid=abc&gclid=def&id=7",
    "https://example.gov/residency?utm_medium=email",
    "https://example.gov/residency?id=1&id=2",
    "https://example.gov/residency?q=a+b&q2=c%20d",
    "https://example.gov/residency?blank=&other=1",
    "https://example.gov/residency#section-3",
    "https://example.gov/",
    "https://example.gov",
    "http://example.gov/a/b/",
    "https://sub.example.gov:8443/path/",
    "https://example.gov/%C3%A4?z=1&a=ä",
    "https://example.gov/residency?ä=1",
    "https://example.gov/residency/?utm_campaign=x&utm_term=y",
]


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("document_normalized_url_migration", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(session: Session, step: Callable[[], None]) -> None:
    session.flush()
    context = MigrationContext.configure(session.connection())
    with Operations.context(context):
        step()
    session.expire_all()


def _jurisdiction(session: Session) -> Jurisdiction:
    row = Jurisdiction(kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Testland"}, code=f"T{uuid.uuid4().hex[:8]}")
    session.add(row)
    session.flush()
    return row


def _reset_to_previous_revision(session: Session) -> None:
    """Remove the column (and with it the index) so the test starts from the pre-migration schema."""
    session.execute(sa.text("ALTER TABLE document DROP COLUMN IF EXISTS normalized_url"))


def _insert_raw(session: Session, jurisdiction: Jurisdiction, slug: str, official_url: str | None) -> uuid.UUID:
    doc_id = uuid.uuid4()
    session.execute(
        sa.text(
            "INSERT INTO document (id, jurisdiction_id, slug, title_i18n, description_i18n, official_url) "
            "VALUES (:id, :jid, :slug, '{}'::jsonb, '{}'::jsonb, :url)"
        ),
        {"id": doc_id, "jid": jurisdiction.id, "slug": slug, "url": official_url},
    )
    return doc_id


def _stored(session: Session, doc_id: uuid.UUID) -> str | None:
    return session.execute(sa.text("SELECT normalized_url FROM document WHERE id = :id"), {"id": doc_id}).scalar_one()


def _index_names(session: Session) -> set[str]:
    return {index["name"] for index in sa.inspect(session.connection()).get_indexes("document")}


def _column_names(session: Session) -> set[str]:
    return {column["name"] for column in sa.inspect(session.connection()).get_columns("document")}


def test_backfill_normalises_existing_rows_and_leaves_missing_urls_null(
    db_session: Session,
) -> None:
    jurisdiction = _jurisdiction(db_session)
    _reset_to_previous_revision(db_session)
    with_url = _insert_raw(db_session, jurisdiction, "residency", "https://Example.gov/residency/?utm_source=x&b=2&a=1")
    without_url = _insert_raw(db_session, jurisdiction, "no-url", None)

    _run(db_session, _load_migration().upgrade)

    assert _stored(db_session, with_url) == "https://example.gov/residency?a=1&b=2"
    assert _stored(db_session, without_url) is None


def test_backfill_adds_the_column_and_the_non_unique_index(db_session: Session) -> None:
    _reset_to_previous_revision(db_session)

    _run(db_session, _load_migration().upgrade)

    assert "normalized_url" in _column_names(db_session)
    assert INDEX_NAME in _index_names(db_session)


def test_backfill_is_idempotent_and_keeps_filled_values(db_session: Session) -> None:
    jurisdiction = _jurisdiction(db_session)
    _reset_to_previous_revision(db_session)
    doc_id = _insert_raw(db_session, jurisdiction, "residency", "https://example.gov/residency/")
    module = _load_migration()
    _run(db_session, module.upgrade)
    db_session.execute(sa.text("UPDATE document SET normalized_url = 'kept' WHERE id = :id"), {"id": doc_id})

    module._backfill_normalized_url(db_session.connection())

    assert _stored(db_session, doc_id) == "kept"


def test_backfill_fills_rows_across_several_batches(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    jurisdiction = _jurisdiction(db_session)
    _reset_to_previous_revision(db_session)
    ids = [_insert_raw(db_session, jurisdiction, f"doc-{n}", f"https://example.gov/{n}/") for n in range(5)]
    module = _load_migration()
    monkeypatch.setattr(module, "BATCH_SIZE", 2)

    _run(db_session, module.upgrade)

    assert [_stored(db_session, doc_id) for doc_id in ids] == [f"https://example.gov/{n}" for n in range(5)]


def test_backfill_matches_the_application_function_on_a_corpus() -> None:
    module = _load_migration()

    for url in CORPUS:
        assert module._normalize_url(url) == normalize_url(url), url


def test_downgrade_drops_column_and_index(db_session: Session) -> None:
    _reset_to_previous_revision(db_session)
    module = _load_migration()
    _run(db_session, module.upgrade)

    _run(db_session, module.downgrade)

    assert "normalized_url" not in _column_names(db_session)
    assert INDEX_NAME not in _index_names(db_session)
