from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.document import Document, DocumentRequirement
from app.models.jurisdiction import Jurisdiction, JurisdictionKind


class DocumentRepository:
    """Persistence for documents and direct requirements."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def _base_select(self, jurisdiction_id: UUID | None) -> Select[tuple[Document]]:
        stmt = select(Document).order_by(Document.slug.asc())
        if jurisdiction_id is not None:
            stmt = stmt.where(Document.jurisdiction_id == jurisdiction_id)
        return stmt

    def count(self, *, jurisdiction_id: UUID | None) -> int:
        stmt = select(func.count()).select_from(Document)
        if jurisdiction_id is not None:
            stmt = stmt.where(Document.jurisdiction_id == jurisdiction_id)
        return int(self._session.scalar(stmt) or 0)

    def list_page(self, *, jurisdiction_id: UUID | None, offset: int, limit: int) -> list[Document]:
        stmt = self._base_select(jurisdiction_id).offset(offset).limit(limit)
        return list(self._session.scalars(stmt).all())

    def get_by_id(self, document_id: UUID) -> Document | None:
        stmt = (
            select(Document)
            .options(selectinload(Document.outgoing_requirements).selectinload(DocumentRequirement.required_document))
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
