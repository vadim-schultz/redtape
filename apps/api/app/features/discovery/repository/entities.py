"""Discovery entity queries and upsert."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.features.discovery.repository.base import SessionRepository
from app.features.discovery.url_normalize import normalize_canonical_url
from app.models.discovery import DiscoveryEntity


class EntityRepository(SessionRepository):
    """Read and write discovery entities."""

    def get_entity(self, entity_id: UUID) -> DiscoveryEntity | None:
        """Return the entity with ``entity_id``, if any."""
        return self._session.get(DiscoveryEntity, entity_id)

    def upsert_entity(
        self, *, catalogue_service_id: UUID, canonical_url: str, label: str | None
    ) -> tuple[DiscoveryEntity, bool]:
        """Insert or update an entity keyed by catalogue row and normalized canonical URL."""
        existing = self._find_by_normalized_url(catalogue_service_id, canonical_url)
        if existing is not None:
            return self._update_entity(existing, canonical_url, label), False
        row = DiscoveryEntity(catalogue_service_id=catalogue_service_id, canonical_url=canonical_url, label=label)
        self._session.add(row)
        self._session.flush()
        return row, True

    def list_catalogue_entities(self, catalogue_id: UUID) -> list[DiscoveryEntity]:
        """Return the entities of one catalogue row, oldest first."""
        stmt = (
            select(DiscoveryEntity)
            .where(DiscoveryEntity.catalogue_service_id == catalogue_id)
            .order_by(DiscoveryEntity.created_at.asc(), DiscoveryEntity.id.asc())
        )
        return list(self._session.scalars(stmt).all())

    def _update_entity(self, entity: DiscoveryEntity, canonical_url: str, label: str | None) -> DiscoveryEntity:
        entity.canonical_url = canonical_url
        if label is not None and label.strip():
            entity.label = label
        self._session.flush()
        return entity

    def _find_by_normalized_url(self, catalogue_service_id: UUID, normalized_url: str) -> DiscoveryEntity | None:
        for entity in self.list_catalogue_entities(catalogue_service_id):
            if normalize_canonical_url(entity.canonical_url) == normalized_url:
                return entity
        return None
