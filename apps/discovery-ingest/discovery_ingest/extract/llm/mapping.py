"""Map grounded model output to the items posted to the machine routes."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from discovery_ingest.edges import EdgeItem
from discovery_ingest.extract.llm.ground_state import Grounded
from discovery_ingest.extract.llm.normalise import name_slug
from discovery_ingest.extract.llm.schema import DependencyItem, DocumentItem
from discovery_ingest.mentions import MentionItem

SOURCE_FIELD = "llm"
EXTRACTOR = "llm"
DEFAULT_LANGUAGE = "de"


@dataclass(frozen=True, slots=True)
class MappingContext:
    """The page facts a mapped item carries: its procedure, snapshot, language and extractor version."""

    catalogue_service_id: UUID
    artifact_id: UUID | None
    language: str | None
    extractor_version: str

    def title(self, name: str) -> dict[str, str]:
        """Return ``name`` keyed by the page language, German when the page declares none."""
        return {self.language or DEFAULT_LANGUAGE: name}


def _mention(document: DocumentItem, grounded: Grounded, ctx: MappingContext) -> MentionItem:
    return MentionItem(
        catalogue_service_id=ctx.catalogue_service_id,
        artifact_id=ctx.artifact_id,
        title_i18n=ctx.title(document.name),
        role=document.role,
        excerpt=document.quote,
        source_field=SOURCE_FIELD,
        extractor=EXTRACTOR,
        extractor_version=ctx.extractor_version,
        official_url=document.url,
        condition=document.condition,
        is_optional=document.is_optional,
        domain_codes=list(grounded.domain_codes),
        situation_codes=list(grounded.situation_codes),
    )


def _explicit_edge(dependency: DependencyItem, ctx: MappingContext) -> EdgeItem:
    return EdgeItem(
        catalogue_service_id=ctx.catalogue_service_id,
        parent_title_i18n=ctx.title(dependency.parent),
        required_title_i18n=ctx.title(dependency.requires),
        basis="explicit",
        condition=dependency.condition,
        excerpt=dependency.quote,
        extractor=EXTRACTOR,
        extractor_version=ctx.extractor_version,
    )


def _derived_edge(issued: DocumentItem, required: DocumentItem, ctx: MappingContext) -> EdgeItem:
    return EdgeItem(
        catalogue_service_id=ctx.catalogue_service_id,
        parent_title_i18n=ctx.title(issued.name),
        required_title_i18n=ctx.title(required.name),
        basis="derived_single_issued",
        condition=required.condition,
        is_optional=required.is_optional,
        excerpt=issued.quote,
        extractor=EXTRACTOR,
        extractor_version=ctx.extractor_version,
    )


def _pair(parent: str, required: str) -> tuple[str, str]:
    return name_slug(parent), name_slug(required)


def _single_issued(documents: Sequence[DocumentItem]) -> DocumentItem | None:
    issued = [document for document in documents if document.role == "issued"]
    return issued[0] if len(issued) == 1 else None


def _needs_derived_edge(issued: DocumentItem, required: DocumentItem, taken: set[tuple[str, str]]) -> bool:
    parent_slug, required_slug = _pair(issued.name, required.name)
    return required.role == "required" and parent_slug != required_slug and (parent_slug, required_slug) not in taken


def _derived_edges(
    documents: Sequence[DocumentItem], taken: set[tuple[str, str]], ctx: MappingContext
) -> list[EdgeItem]:
    issued = _single_issued(documents)
    if issued is None:
        return []
    return [_derived_edge(issued, doc, ctx) for doc in documents if _needs_derived_edge(issued, doc, taken)]


def to_items(grounded: Grounded, ctx: MappingContext) -> tuple[list[MentionItem], list[EdgeItem]]:
    """Return the mentions of the documents and the explicit and derived edges between them."""
    mentions = [_mention(document, grounded, ctx) for document in grounded.documents]
    explicit = [_explicit_edge(dependency, ctx) for dependency in grounded.dependencies]
    taken = {_pair(dep.parent, dep.requires) for dep in grounded.dependencies}
    return mentions, explicit + _derived_edges(grounded.documents, taken, ctx)
