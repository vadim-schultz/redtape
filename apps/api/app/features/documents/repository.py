"""Persistence for documents, their category links, direct requirements and the jurisdiction tree."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import ColumnElement, Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.document import Document, DocumentRequirement
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.taxonomy import Category, document_category


def _category_filter(stmt: Select, category_ids: Sequence[UUID]) -> Select:
    """Keep the documents linked to any of ``category_ids``; no ids keeps every document."""
    if not category_ids:
        return stmt
    linked = (
        select(1)
        .where(document_category.c.document_id == Document.id, document_category.c.category_id.in_(category_ids))
        .exists()
    )
    return stmt.where(linked)


def _order_by(category_ids: Sequence[UUID]) -> tuple:
    """Order by slug, or by the highest matched category confidence first with the slug as the tiebreak."""
    if not category_ids:
        return (Document.slug.asc(),)
    link = document_category
    max_confidence = (
        select(func.max(link.c.confidence))
        .where(link.c.document_id == Document.id, link.c.category_id.in_(category_ids))
        .scalar_subquery()
    )
    return (max_confidence.desc(), Document.slug.asc())


def _provenance(code: str, leaf_codes: dict[str, str]) -> dict[str, str]:
    """Return a category link's provenance: the promotion source, and the PVOG leaf it came from when one was given."""
    provenance = {"source": "category_code_promotion"}
    if code in leaf_codes:
        provenance["pvog_leaf_code"] = leaf_codes[code]
    return provenance


class DocumentRepository:
    """Persistence for documents and direct requirements."""

    def __init__(self, session: Session) -> None:
        """Bind the repository to the request's database session."""
        self._session = session

    def _base_select(self, jurisdiction_id: UUID | None, category_ids: Sequence[UUID]) -> Select:
        stmt = select(Document).order_by(*_order_by(category_ids))
        if jurisdiction_id is not None:
            stmt = stmt.where(Document.jurisdiction_id == jurisdiction_id)
        return _category_filter(stmt, category_ids)

    def count(self, *, jurisdiction_id: UUID | None, category_ids: Sequence[UUID] = ()) -> int:
        """Count documents matching the jurisdiction and category filters, ignoring pagination."""
        filtered = self._base_select(jurisdiction_id, category_ids).order_by(None).subquery()
        return int(self._session.scalar(select(func.count()).select_from(filtered)) or 0)

    def list_page(
        self,
        *,
        jurisdiction_id: UUID | None,
        offset: int,
        limit: int,
        category_ids: Sequence[UUID] = (),
    ) -> list[Document]:
        """Return one page of matching documents in the repository ordering."""
        stmt = self._base_select(jurisdiction_id, category_ids).offset(offset).limit(limit)
        return list(self._session.scalars(stmt).all())

    def add(
        self,
        document: Document,
        *,
        category_scores: dict[str, float],
        pvog_leaf_codes: dict[str, str] | None = None,
    ) -> Document:
        """Insert a document and flush it, then link each category with its confidence and PVOG provenance."""
        self._session.add(document)
        self._session.flush()
        self._link_categories(document.id, category_scores, pvog_leaf_codes or {})
        return document

    def _link_categories(self, document_id: UUID, scores: dict[str, float], leaf_codes: dict[str, str]) -> None:
        """Insert one category link per score; an unknown category code is rejected before any row is written."""
        if not scores:
            return
        known = self._category_ids(scores)
        unknown = sorted(set(scores) - known.keys())
        if unknown:
            raise ValueError(f"Unknown category code(s): {', '.join(unknown)}")
        self._session.execute(
            document_category.insert(),
            [
                {
                    "document_id": document_id,
                    "category_id": known[code],
                    "confidence": confidence,
                    "source": "promotion",
                    "provenance": _provenance(code, leaf_codes),
                }
                for code, confidence in scores.items()
            ],
        )

    def _category_ids(self, codes: dict[str, float]) -> dict[str, UUID]:
        rows = self._session.execute(select(Category.code, Category.id).where(Category.code.in_(set(codes)))).all()
        return {code: category_id for code, category_id in rows}

    def get_by_id(self, document_id: UUID) -> Document | None:
        """Return the document with its requirements and categories eager-loaded, or `None` when absent."""
        stmt = (
            select(Document)
            .options(
                selectinload(Document.outgoing_requirements).selectinload(DocumentRequirement.required_document),
                selectinload(Document.categories),
            )
            .where(Document.id == document_id)
        )
        return self._session.scalar(stmt)

    def get_category_confidence(self, document_id: UUID) -> dict[UUID, float]:
        """Return the persisted confidence of every category link of ``document_id``, keyed by category id."""
        link = document_category
        stmt = select(link.c.category_id, link.c.confidence).where(link.c.document_id == document_id)
        return dict(self._session.execute(stmt).tuples().all())

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

    def find_conflicting_document_ids(
        self, *, jurisdiction_id: UUID, slug: str, normalized_url: str | None
    ) -> list[UUID]:
        """Ids of documents in the jurisdiction whose slug or stored normalized URL equals the candidate's.

        The URL arm is left out when the candidate has no normalized URL, so a URL-less candidate matches on the
        slug alone. Ordered by ``created_at, id`` for stability; callers only test membership.
        """
        clash: ColumnElement[bool] = Document.slug == slug
        if normalized_url is not None:
            clash = or_(clash, Document.normalized_url == normalized_url)
        stmt = (
            select(Document.id)
            .where(Document.jurisdiction_id == jurisdiction_id, clash)
            .order_by(Document.created_at, Document.id)
        )
        return list(self._session.scalars(stmt))

    def jurisdiction_exists(self, jurisdiction_id: UUID) -> bool:
        """Return whether a jurisdiction with this id exists."""
        return self._session.scalar(select(Jurisdiction.id).where(Jurisdiction.id == jurisdiction_id)) is not None

    def get_municipality_jurisdiction_id(self, *, municipality_code: str) -> UUID | None:
        """Resolve OpenPLZ municipality code → our jurisdiction UUID."""
        stmt = select(Jurisdiction).where(
            Jurisdiction.kind == JurisdictionKind.MUNICIPALITY,
            Jurisdiction.code == municipality_code,
        )
        row = self._session.scalar(stmt)
        return row.id if row is not None else None

    def get_jurisdiction_for_document(self, document_id: UUID) -> UUID | None:
        """Return the jurisdiction id of a document, or `None` when the document does not exist."""
        return self._session.scalar(select(Document.jurisdiction_id).where(Document.id == document_id))

    def find_requirement(
        self, *, jurisdiction_id: UUID, parent_document_id: UUID, required_document_id: UUID
    ) -> UUID | None:
        """Return the id of the requirement between two documents in a jurisdiction, or `None`."""
        stmt = select(DocumentRequirement.id).where(
            DocumentRequirement.jurisdiction_id == jurisdiction_id,
            DocumentRequirement.parent_document_id == parent_document_id,
            DocumentRequirement.required_document_id == required_document_id,
        )
        return self._session.scalar(stmt)

    def add_requirement(self, requirement: DocumentRequirement) -> DocumentRequirement:
        """Insert a requirement and flush it so its id is available to the caller."""
        self._session.add(requirement)
        self._session.flush()
        return requirement

    def requirement_edge_exists(self, *, parent_document_id: UUID, required_document_id: UUID) -> bool:
        """Whether `parent_document_id` already directly requires `required_document_id`, in any jurisdiction."""
        stmt = select(DocumentRequirement.id).where(
            DocumentRequirement.parent_document_id == parent_document_id,
            DocumentRequirement.required_document_id == required_document_id,
        )
        return self._session.scalar(stmt) is not None
