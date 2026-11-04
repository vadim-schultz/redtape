"""Dependency providers for the taxonomy feature."""

from __future__ import annotations

from litestar.di import Provide
from sqlalchemy.orm import Session

from app.features.taxonomy.repository import TaxonomyRepository
from app.features.taxonomy.service import TaxonomyService


def provide_taxonomy_repository(session: Session) -> TaxonomyRepository:
    """Bind a taxonomy repository to the request session."""
    return TaxonomyRepository(session)


def provide_taxonomy_service(taxonomy_repository: TaxonomyRepository) -> TaxonomyService:
    """Bind the taxonomy service to its repository."""
    return TaxonomyService(taxonomy_repository)


router_dependencies = {
    "taxonomy_repository": Provide(provide_taxonomy_repository, sync_to_thread=False),
    "taxonomy_service": Provide(provide_taxonomy_service, sync_to_thread=False),
}
