from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import Column, Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.document import Document, DocumentRequirement
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.taxonomy import document_domain, document_life_situation


def _filter_by_terms(
    stmt: Select[tuple[Document]], term_column: Column, ids: Sequence[UUID]
) -> Select[tuple[Document]]:
    """Keep documents linked to any of `ids` through the link table owning `term_column`; no ids, no filter."""
    if not ids:
        return stmt
    link = term_column.table
    return stmt.where(select(1).where(link.c.document_id == Document.id, term_column.in_(ids)).exists())


class DocumentRepository:
    """Persistence for documents and direct requirements."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def _base_select(
        self,
        jurisdiction_id: UUID | None,
        domain_ids: Sequence[UUID],
        situation_ids: Sequence[UUID],
    ) -> Select[tuple[Document]]:
        stmt = select(Document).order_by(Document.slug.asc())
        if jurisdiction_id is not None:
            stmt = stmt.where(Document.jurisdiction_id == jurisdiction_id)
        stmt = _filter_by_terms(stmt, document_domain.c.domain_id, domain_ids)
        return _filter_by_terms(stmt, document_life_situation.c.life_situation_id, situation_ids)

    def count(
        self,
        *,
        jurisdiction_id: UUID | None,
        domain_ids: Sequence[UUID] = (),
        situation_ids: Sequence[UUID] = (),
    ) -> int:
        filtered = self._base_select(jurisdiction_id, domain_ids, situation_ids).order_by(None).subquery()
        return int(self._session.scalar(select(func.count()).select_from(filtered)) or 0)

    def list_page(
        self,
        *,
        jurisdiction_id: UUID | None,
        offset: int,
        limit: int,
        domain_ids: Sequence[UUID] = (),
        situation_ids: Sequence[UUID] = (),
    ) -> list[Document]:
        stmt = self._base_select(jurisdiction_id, domain_ids, situation_ids).offset(offset).limit(limit)
        return list(self._session.scalars(stmt).all())

    def get_by_id(self, document_id: UUID) -> Document | None:
        stmt = (
            select(Document)
            .options(
                selectinload(Document.outgoing_requirements).selectinload(DocumentRequirement.required_document),
                selectinload(Document.domains),
                selectinload(Document.life_situations),
            )
            .where(Document.id == document_id)
        )
        return self._session.scalar(stmt)

    def get_jurisdiction_path(self, *, jurisdiction_id: UUID) -> list[Jurisdiction]:
        """Walk `geographic_parent_id` links to build a root → leaf breadcrumb."""
        path: list[Jurisdiction] = []
        current_id: UUID | None = jurisdiction_id
        # Safety cap to avoid cycles in bad data.
        for _ in range(10):
            if current_id is None:
                break
            row = self._session.scalar(select(Jurisdiction).where(Jurisdiction.id == current_id))
            if row is None:
                break
            path.append(row)
            current_id = row.geographic_parent_id
        path.reverse()
        return path

    def get_municipality_jurisdiction_id(self, *, municipality_code: str) -> UUID | None:
        """Resolve OpenPLZ municipality code → our jurisdiction UUID."""
        stmt = select(Jurisdiction).where(
            Jurisdiction.kind == JurisdictionKind.MUNICIPALITY,
            Jurisdiction.code == municipality_code,
        )
        row = self._session.scalar(stmt)
        return row.id if row is not None else None
