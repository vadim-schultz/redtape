"""The data migration removes exactly the four seeded sample documents and nothing else."""

from __future__ import annotations

import importlib.util
import uuid
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from app.models.document import Document, DocumentRequirement
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.taxonomy import Domain, document_domain
from sqlalchemy.orm import Session

MIGRATION = Path(__file__).resolve().parent.parent / "alembic" / "versions" / "20261102_remove_seeded_documents.py"

SEEDED_DOC_IDS = [uuid.UUID(f"22222222-2222-2222-2222-2222222222{n:02d}") for n in (1, 2, 3, 4)]
SEEDED_REQ_IDS = [uuid.UUID(f"33333333-3333-3333-3333-3333333333{n:02d}") for n in (1, 2, 3)]


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("remove_seeded_documents_migration", MIGRATION)
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


def _upgrade(session: Session) -> None:
    _run(session, _load_migration().upgrade)


def _count(session: Session, table: type | sa.Table) -> int:
    return session.execute(sa.select(sa.func.count()).select_from(table)).scalar_one()


def _jurisdiction(session: Session, code: str) -> Jurisdiction:
    row = Jurisdiction(kind=JurisdictionKind.COUNTRY, geographic_parent_id=None, code=code)
    session.add(row)
    session.flush()
    return row


def _document(session: Session, jurisdiction: Jurisdiction, slug: str, doc_id: uuid.UUID | None = None) -> Document:
    row = Document(id=doc_id or uuid.uuid4(), jurisdiction_id=jurisdiction.id, slug=slug, title_i18n={"en": slug})
    session.add(row)
    session.flush()
    return row


def _edge(
    session: Session, jurisdiction: Jurisdiction, parent: Document, required: Document, row_id: uuid.UUID
) -> None:
    session.add(
        DocumentRequirement(
            id=row_id,
            parent_document_id=parent.id,
            required_document_id=required.id,
            jurisdiction_id=jurisdiction.id,
        )
    )
    session.flush()


def _tag(session: Session, document: Document, domain: Domain) -> None:
    session.execute(sa.insert(document_domain).values(document_id=document.id, domain_id=domain.id))


def _domain(session: Session) -> Domain:
    row = Domain(code="housing", name_i18n={"en": "Housing"}, description_i18n={"en": "Housing"})
    session.add(row)
    session.flush()
    return row


def _seed_samples(session: Session, jurisdiction: Jurisdiction, domain: Domain) -> None:
    docs = [_document(session, jurisdiction, f"sample-{i}", doc_id) for i, doc_id in enumerate(SEEDED_DOC_IDS)]
    for doc, req_id in zip(docs[1:], SEEDED_REQ_IDS, strict=True):
        _edge(session, jurisdiction, docs[0], doc, req_id)
    for doc in docs:
        _tag(session, doc, domain)


def test_upgrade_removes_the_seeded_documents_requirements_and_tag_links(db_session: Session) -> None:
    jurisdiction, domain = _jurisdiction(db_session, "DE"), _domain(db_session)
    _seed_samples(db_session, jurisdiction, domain)

    _upgrade(db_session)

    assert [_count(db_session, t) for t in (Document, DocumentRequirement, document_domain)] == [0, 0, 0]


def test_upgrade_keeps_a_non_seed_document_with_the_same_slug_its_tags_and_its_edge(db_session: Session) -> None:
    de, other, domain = _jurisdiction(db_session, "DE"), _jurisdiction(db_session, "AT"), _domain(db_session)
    _seed_samples(db_session, de, domain)
    kept_parent = _document(db_session, other, "sample-0")
    kept_required = _document(db_session, other, "sample-1")
    kept_edge_id = uuid.uuid4()
    _edge(db_session, other, kept_parent, kept_required, kept_edge_id)
    _tag(db_session, kept_parent, domain)

    _upgrade(db_session)

    assert {d.id for d in db_session.scalars(sa.select(Document))} == {kept_parent.id, kept_required.id}
    assert db_session.scalars(sa.select(DocumentRequirement.id)).all() == [kept_edge_id]
    assert db_session.execute(sa.select(document_domain.c.document_id)).scalars().all() == [kept_parent.id]


def test_upgrade_deletes_an_edge_between_a_seed_and_a_non_seed_document(db_session: Session) -> None:
    de, domain = _jurisdiction(db_session, "DE"), _domain(db_session)
    _seed_samples(db_session, de, domain)
    survivor = _document(db_session, de, "real-document")
    _edge(db_session, de, survivor, db_session.get(Document, SEEDED_DOC_IDS[0]), uuid.uuid4())

    _upgrade(db_session)

    assert db_session.scalars(sa.select(Document.id)).all() == [survivor.id]
    assert _count(db_session, DocumentRequirement) == 0


def test_upgrade_on_a_database_without_the_seeded_rows_is_a_no_op(db_session: Session) -> None:
    jurisdiction = _jurisdiction(db_session, "DE")
    survivor = _document(db_session, jurisdiction, "real-document")

    _upgrade(db_session)
    _upgrade(db_session)

    assert db_session.scalars(sa.select(Document.id)).all() == [survivor.id]


def test_downgrade_is_an_irreversible_no_op(db_session: Session) -> None:
    jurisdiction = _jurisdiction(db_session, "DE")
    survivor = _document(db_session, jurisdiction, "real-document")

    _run(db_session, _load_migration().downgrade)

    assert db_session.scalars(sa.select(Document.id)).all() == [survivor.id]
