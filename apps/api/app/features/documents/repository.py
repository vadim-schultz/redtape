"""Persistence for documents, their tag links, direct requirements and the jurisdiction tree."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import Column, ColumnElement, Select, and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.document import Document, DocumentRequirement
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.taxonomy import Category, document_category, document_domain, document_life_situation


@dataclass(frozen=True)
class TagConfidenceMaps:
    """A document's persisted tag confidence, keyed by term id, for each axis."""

    domains: dict[UUID, float]
    life_situations: dict[UUID, float]
    categories: dict[UUID, float] = field(default_factory=dict)


def _confidence_map(session: Session, term_column: Column, document_id: UUID) -> dict[UUID, float]:
    link = term_column.table
    stmt = select(term_column, link.c.confidence).where(link.c.document_id == document_id)
    return dict(session.execute(stmt).tuples().all())


def _category_or_legacy_filter(
    stmt: Select[tuple[Document]],
    category_ids: Sequence[UUID],
    domain_category_ids: Sequence[UUID],
    situation_category_ids: Sequence[UUID],
    domain_ids: Sequence[UUID],
    situation_ids: Sequence[UUID],
) -> Select[tuple[Document]]:
    """Use canonical links when present, with legacy links as the transition fallback."""
    legacy_conditions: list[ColumnElement[bool]] = []
    if domain_ids:
        legacy_domain: ColumnElement[bool] = (
            select(1)
            .where(document_domain.c.document_id == Document.id, document_domain.c.domain_id.in_(domain_ids))
            .exists()
        )
        if domain_category_ids:
            legacy_domain = or_(
                legacy_domain,
                select(1)
                .where(
                    document_category.c.document_id == Document.id,
                    document_category.c.category_id.in_(domain_category_ids),
                )
                .exists(),
            )
        legacy_conditions.append(legacy_domain)
    if situation_ids:
        legacy_situation: ColumnElement[bool] = (
            select(1)
            .where(
                document_life_situation.c.document_id == Document.id,
                document_life_situation.c.life_situation_id.in_(situation_ids),
            )
            .exists()
        )
        if situation_category_ids:
            legacy_situation = or_(
                legacy_situation,
                select(1)
                .where(
                    document_category.c.document_id == Document.id,
                    document_category.c.category_id.in_(situation_category_ids),
                )
                .exists(),
            )
        legacy_conditions.append(legacy_situation)
    if legacy_conditions:
        return stmt.where(and_(*legacy_conditions))
    if not category_ids:
        return stmt
    canonical = (
        select(1)
        .where(document_category.c.document_id == Document.id, document_category.c.category_id.in_(category_ids))
        .exists()
    )
    return stmt.where(canonical)


def _order_by(category_ids: Sequence[UUID], situation_ids: Sequence[UUID]) -> tuple:
    """Order by slug, or by the highest matched category or situation confidence.

    With a taxonomy filter the highest matched confidence comes first and the slug is the tiebreak
    (situation-tag-hierarchy chapter 4; `max` across multiple selected situations is a documented
    open seam, see `gaps-and-decisions.md`).
    """
    if category_ids:
        link = document_category
        max_confidence = (
            select(func.max(link.c.confidence))
            .where(link.c.document_id == Document.id, link.c.category_id.in_(category_ids))
            .scalar_subquery()
        )
        return (max_confidence.desc(), Document.slug.asc())
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
        """Bind the repository to the request's database session."""
        self._session = session

    def _base_select(
        self,
        jurisdiction_id: UUID | None,
        category_ids: Sequence[UUID],
        domain_category_ids: Sequence[UUID],
        situation_category_ids: Sequence[UUID],
        domain_ids: Sequence[UUID],
        situation_ids: Sequence[UUID],
    ) -> Select[tuple[Document]]:
        stmt = select(Document).order_by(*_order_by(category_ids, situation_ids))
        if jurisdiction_id is not None:
            stmt = stmt.where(Document.jurisdiction_id == jurisdiction_id)
        return _category_or_legacy_filter(
            stmt,
            category_ids,
            domain_category_ids,
            situation_category_ids,
            domain_ids,
            situation_ids,
        )

    def count(
        self,
        *,
        jurisdiction_id: UUID | None,
        category_ids: Sequence[UUID] = (),
        domain_category_ids: Sequence[UUID] = (),
        situation_category_ids: Sequence[UUID] = (),
        domain_ids: Sequence[UUID] = (),
        situation_ids: Sequence[UUID] = (),
    ) -> int:
        """Count documents matching the jurisdiction and tag filters, ignoring pagination."""
        filtered = (
            self._base_select(
                jurisdiction_id,
                category_ids,
                domain_category_ids,
                situation_category_ids,
                domain_ids,
                situation_ids,
            )
            .order_by(None)
            .subquery()
        )
        return int(self._session.scalar(select(func.count()).select_from(filtered)) or 0)

    def ids_in_scope(self, *, jurisdiction_id: UUID | None) -> list[UUID]:
        """Return the ids of every document in a jurisdiction, or of all documents when none is given."""
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
        category_ids: Sequence[UUID] = (),
        domain_category_ids: Sequence[UUID] = (),
        situation_category_ids: Sequence[UUID] = (),
        domain_ids: Sequence[UUID] = (),
        situation_ids: Sequence[UUID] = (),
    ) -> list[Document]:
        """Return one page of matching documents in the repository ordering."""
        stmt = (
            self._base_select(
                jurisdiction_id,
                category_ids,
                domain_category_ids,
                situation_category_ids,
                domain_ids,
                situation_ids,
            )
            .offset(offset)
            .limit(limit)
        )
        return list(self._session.scalars(stmt).all())

    def add(
        self,
        document: Document,
        *,
        domain_scores: dict[UUID, float] | None = None,
        situation_scores: dict[UUID, float] | None = None,
        situation_leaf_codes: dict[UUID, str] | None = None,
        category_scores: dict[str, float] | None = None,
    ) -> Document:
        """Insert a document and flush it, then link its domain and situation tags from the given scores."""
        self._session.add(document)
        self._session.flush()
        self._link_terms(document_domain.c.domain_id, document.id, domain_scores or {})
        self._link_terms(
            document_life_situation.c.life_situation_id,
            document.id,
            situation_scores or {},
            leaf_codes=situation_leaf_codes or {},
        )
        self._link_categories(document.id, category_scores or {})
        return document

    def _link_categories(self, document_id: UUID, scores: dict[str, float]) -> None:
        """Link canonical category codes when a caller is already on the target write path."""
        if not scores:
            return
        ids = self._session.execute(select(Category.code, Category.id).where(Category.code.in_(set(scores)))).all()
        known = {code: category_id for code, category_id in ids}
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
                    "provenance": {"source": "category_code_promotion"},
                }
                for code, confidence in scores.items()
            ],
        )

    def _link_terms(
        self,
        term_column: Column,
        document_id: UUID,
        scores: dict[UUID, float],
        *,
        leaf_codes: dict[UUID, str] | None = None,
    ) -> None:
        """Insert one link row per ``scores`` entry, carrying its confidence and any PVOG leaf code.

        The PVOG leaf code is the situation-only facet (situation-tag-hierarchy chapter 3).
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
        """Return the document with its requirements and tags eager-loaded, or `None` when absent."""
        stmt = (
            select(Document)
            .options(
                selectinload(Document.outgoing_requirements).selectinload(DocumentRequirement.required_document),
                selectinload(Document.domains),
                selectinload(Document.life_situations),
                selectinload(Document.categories),
            )
            .where(Document.id == document_id)
        )
        return self._session.scalar(stmt)

    def leaf_codes_in_scope(self, *, jurisdiction_id: UUID | None, situation_ids: Sequence[UUID]) -> list[str]:
        """Return the distinct non-null PVOG leaf codes in the given jurisdiction and situation scope.

        Same scope shape as the document list; the result is sorted.
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
            _confidence_map(self._session, document_category.c.category_id, document_id),
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
