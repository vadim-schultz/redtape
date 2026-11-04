"""Dependency providers for the documents feature."""

from __future__ import annotations

from litestar.di import Provide
from sqlalchemy.orm import Session

from app.features.documents.promotion import DocumentPromotion
from app.features.documents.query import provide_document_list_query
from app.features.documents.repository import DocumentRepository
from app.features.documents.service import DocumentService
from app.features.taxonomy.dependencies import router_dependencies as taxonomy_dependencies
from app.features.taxonomy.service import TaxonomyService


def provide_document_repository(session: Session) -> DocumentRepository:
    """Build the document repository on the request's database session."""
    return DocumentRepository(session)


def provide_document_service(
    document_repository: DocumentRepository,
    taxonomy_service: TaxonomyService,
) -> DocumentService:
    """Build the document service on the repository and the taxonomy lookups."""
    return DocumentService(document_repository, taxonomy_service)


def provide_document_promotion(
    document_repository: DocumentRepository,
    taxonomy_service: TaxonomyService,
) -> DocumentPromotion:
    """Build the promotion workflow on the repository and the taxonomy lookups."""
    return DocumentPromotion(document_repository, taxonomy_service)


router_dependencies = {
    **taxonomy_dependencies,
    "document_repository": Provide(provide_document_repository, sync_to_thread=False),
    "document_service": Provide(provide_document_service, sync_to_thread=False),
    "document_promotion": Provide(provide_document_promotion, sync_to_thread=False),
    "document_query": Provide(provide_document_list_query, sync_to_thread=False),
}
