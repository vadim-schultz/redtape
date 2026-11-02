"""Map document and jurisdiction rows to localized read schemas."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from app.features.documents.repository import TagConfidenceMaps
from app.features.taxonomy.service import TaxonomyService
from app.i18n_resolution import pick_i18n
from app.models.document import Document, DocumentRequirement
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.taxonomy import Domain, LifeSituation
from app.schema.document.read import (
    DocumentDetail,
    DocumentSummary,
    JurisdictionPathNode,
    RequirementRead,
    TaggedTermRead,
)

_FIXED_KIND_LABELS = {
    JurisdictionKind.COUNTRY: "COUNTRY",
    JurisdictionKind.MUNICIPALITY: "MUNICIPALITY",
}


@dataclass(frozen=True)
class Locales:
    """The caller's locale and the set of enabled locales."""

    locale: str
    enabled: set[str]


def jurisdiction_kind_label(jurisdiction: Jurisdiction) -> str:
    """Label a jurisdiction; a REGION with the DISTRICT role is shown as DISTRICT."""
    fixed = _FIXED_KIND_LABELS.get(jurisdiction.kind)
    if fixed is not None:
        return fixed
    return "DISTRICT" if "DISTRICT" in (jurisdiction.administrative_roles or []) else "REGION"


class DocumentReadMapper:
    """Build localized read models from document rows."""

    def __init__(self, taxonomy: TaxonomyService) -> None:
        """Bind the mapper to the taxonomy service used for term labels."""
        self._taxonomy = taxonomy

    def summary(self, doc: Document, locales: Locales) -> DocumentSummary:
        """Map a document to its list summary."""
        return DocumentSummary(
            id=doc.id,
            slug=doc.slug,
            title=pick_i18n(doc.title_i18n, locale=locales.locale, enabled=locales.enabled),
            description=pick_i18n(doc.description_i18n, locale=locales.locale, enabled=locales.enabled),
        )

    def detail(
        self, doc: Document, path: Sequence[Jurisdiction], locales: Locales, confidence: TagConfidenceMaps
    ) -> DocumentDetail:
        """Map a document, its jurisdiction path, relations and persisted tag confidence to the detail view."""
        summary = self.summary(doc, locales)
        return DocumentDetail(
            id=doc.id,
            slug=doc.slug,
            title=summary.title,
            description=summary.description,
            official_url=doc.official_url,
            jurisdiction_id=doc.jurisdiction_id,
            jurisdiction_path=[self.path_node(j, locales) for j in path],
            requirements=[self.requirement(edge, locales) for edge in doc.outgoing_requirements],
            domains=self._tagged_term_reads(doc.domains, confidence.domains, locales),
            life_situations=self._tagged_term_reads(doc.life_situations, confidence.life_situations, locales),
        )

    def requirement(self, edge: DocumentRequirement, locales: Locales) -> RequirementRead:
        """Map a requirement edge to its read model."""
        notes = pick_i18n(edge.notes_i18n, locale=locales.locale, enabled=locales.enabled)
        return RequirementRead(
            id=edge.id,
            required_document=self.summary(edge.required_document, locales),
            notes=notes or None,
        )

    def path_node(self, jurisdiction: Jurisdiction, locales: Locales) -> JurisdictionPathNode:
        """Map a jurisdiction to a breadcrumb node."""
        return JurisdictionPathNode(
            code=str(jurisdiction.code or ""),
            name=pick_i18n(jurisdiction.name_i18n, locale=locales.locale, enabled=locales.enabled),
            kind=jurisdiction_kind_label(jurisdiction),
            openplz_type=jurisdiction.openplz_type,
        )

    def _tagged_term_reads(
        self, terms: Sequence[Domain | LifeSituation], confidence: dict[UUID, float], locales: Locales
    ) -> list[TaggedTermRead]:
        return [
            TaggedTermRead.from_term_read(
                self._taxonomy.to_term_read(term, locale=locales.locale, enabled_locales=locales.enabled),
                confidence.get(term.id, 1.0),
            )
            for term in terms
        ]
