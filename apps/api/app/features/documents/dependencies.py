"""Dependency providers for the documents feature."""

from __future__ import annotations

from litestar.di import Provide
from sqlalchemy.orm import Session

from app.features.documents.repository import DocumentRepository
from app.features.documents.service import DocumentService


def provide_document_repository(session: Session) -> DocumentRepository:
    return DocumentRepository(session)


def provide_document_service(document_repository: DocumentRepository) -> DocumentService:
    return DocumentService(document_repository)


router_dependencies = {
    "document_repository": Provide(provide_document_repository, sync_to_thread=False),
    "document_service": Provide(provide_document_service, sync_to_thread=False),
}
