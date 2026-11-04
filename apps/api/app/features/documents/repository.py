from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Column, ColumnElement, Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.document import Document, DocumentRequirement
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.taxonomy import document_domain, document_life_situation


@dataclass(frozen=True)
class TagConfidenceMaps:
    """A document's persisted tag confidence, keyed by term id, for each axis."""

    domains: dict[UUID, float]
    life_situations: dict[UUID, float]


def _confidence_map(session: Session, term_column: Column, document_id: UUID) -> dict[UUID, float]:
    link = term_column.table
    stmt = select(term_column, link.c.confidence).where(link.c.document_id == document_id)
    return dict(session.execute(stmt).tuples().all())


def _filter_by_terms(
    stmt: Select[tuple[Document]], term_column: Column, ids: Sequence[UUID]
) -> Select[tuple[Document]]:
    """Keep documents linked to any of `ids` through the link table owning `term_column`; no ids, no filter."""
    if not ids:
        return stmt
    link = term_column.table
    return stmt.where(select(1).where(link.c.document_id == Document.id, term_column.in_(ids)).exists())


def _order_by(situation_ids: Sequence[UUID]) -> tuple:
    """Slug order, unless a situation filter is active — then the highest matched confidence first
    (situation-tag-hierarchy chapter 4; `max` across multiple selected situations is a documented
    open seam, see `gaps-and-decisions.md`), slug still the tiebreak.
    """
    if not situation_ids:
        return (Document.slug.asc(),)
    link = document_life_situation
    max_confidence = (
        select(func.max(link.c.confidence))
        .where(link.c.document_id == Document.id, link.c.life_situation_id.in_(situation_ids))
        .scalar_subquery()
    )
    return (max_confidence.desc(), Document.slug.asc())


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
        stmt = select(Document).order_by(*_order_by(situation_ids))
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

    def ids_in_scope(self, *, jurisdiction_id: UUID | None) -> list[UUID]:
        stmt = select(Document.id)
        if jurisdiction_id is not None:
            stmt = stmt.where(Document.jurisdiction_id == jurisdiction_id)
        return list(self._session.scalars(stmt).all())

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

    def add(
        self,
        document: Document,
        *,
        domain_scores: dict[UUID, float] | None = None,
        situation_scores: dict[UUID, float] | None = None,
        situation_leaf_codes: dict[UUID, str] | None = None,
    ) -> Document:
        self._session.add(document)
        self._session.flush()
        self._link_terms(document_domain.c.domain_id, document.id, domain_scores or {})
        self._link_terms(
            document_life_situation.c.life_situation_id,
            document.id,
            situation_scores or {},
            leaf_codes=situation_leaf_codes or {},
        )
        return document

    def _link_terms(
        self,
        term_column: Column,
        document_id: UUID,
        scores: dict[UUID, float],
        *,
        leaf_codes: dict[UUID, str] | None = None,
    ) -> None:
        """Insert one link row per ``scores`` entry, each carrying its given confidence and, when given,
        its PVOG leaf code (situation-only facet, situation-tag-hierarchy chapter 3).

        ``scores`` must already carry every id that is to be linked — a missing id is not defaulted here;
        that's the caller's contract, one layer up (``DocumentService._resolve_tags``).
        """
        if not scores:
            return
        leaf_codes = leaf_codes or {}
        rows = [
            {
                "document_id": document_id,
                term_column.name: term_id,
                "confidence": score,
                **({"pvog_leaf_code": leaf_codes[term_id]} if term_id in leaf_codes else {}),
            }
            for term_id, score in scores.items()
        ]
        self._session.execute(term_column.table.insert(), rows)

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

    def leaf_codes_in_scope(self, *, jurisdiction_id: UUID | None, situation_ids: Sequence[UUID]) -> list[str]:
        """Distinct non-null PVOG leaf codes among `document_life_situation` rows matching the given
        jurisdiction/situation scope, same shape as `_base_select`/`_filter_by_terms`.
        """
        link = document_life_situation
        stmt = (
            select(link.c.pvog_leaf_code)
            .distinct()
            .where(link.c.pvog_leaf_code.is_not(None), link.c.life_situation_id.in_(situation_ids))
        )
        if jurisdiction_id is not None:
            stmt = stmt.where(
                select(1).where(Document.id == link.c.document_id, Document.jurisdiction_id == jurisdiction_id).exists()
            )
        return sorted(self._session.scalars(stmt).all())

    def get_tag_confidence(self, document_id: UUID) -> TagConfidenceMaps:
        """Return the persisted confidence of every domain and life-situation tag of ``document_id``."""
        return TagConfidenceMaps(
            _confidence_map(self._session, document_domain.c.domain_id, document_id),
            _confidence_map(self._session, document_life_situation.c.life_situation_id, document_id),
        )

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
        return self._session.scalar(select(Document.jurisdiction_id).where(Document.id == document_id))

    def find_requirement(
        self, *, jurisdiction_id: UUID, parent_document_id: UUID, required_document_id: UUID
    ) -> UUID | None:
        stmt = select(DocumentRequirement.id).where(
            DocumentRequirement.jurisdiction_id == jurisdiction_id,
            DocumentRequirement.parent_document_id == parent_document_id,
            DocumentRequirement.required_document_id == required_document_id,
        )
        return self._session.scalar(stmt)

    def add_requirement(self, requirement: DocumentRequirement) -> DocumentRequirement:
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
