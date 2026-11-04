"""Discovery claim queries."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.features.discovery.repository.base import SessionRepository
from app.models.discovery import DiscoveryClaim, DiscoveryClaimKind, DiscoveryEntity


class ClaimRepository(SessionRepository):
    """Read and add discovery claims; fingerprinting and race recovery live in the claim service."""

    def find_claim_by_fingerprint(
        self,
        *,
        discovery_entity_id: UUID,
        kind: DiscoveryClaimKind,
        payload_fingerprint: str,
    ) -> DiscoveryClaim | None:
        """Return the claim of ``kind`` with ``payload_fingerprint`` on one entity, if any."""
        stmt = (
            select(DiscoveryClaim)
            .where(
                DiscoveryClaim.discovery_entity_id == discovery_entity_id,
                DiscoveryClaim.kind == kind,
                DiscoveryClaim.payload_fingerprint == payload_fingerprint,
            )
            .limit(1)
        )
        return self._session.scalar(stmt)

    def add_claim(self, row: DiscoveryClaim) -> None:
        """Add ``row`` to the session and flush it."""
        self._session.add(row)
        self._session.flush()

    def list_catalogue_claims(self, catalogue_id: UUID) -> list[DiscoveryClaim]:
        """Return the claims of one catalogue row, oldest first."""
        stmt = (
            select(DiscoveryClaim)
            .join(DiscoveryEntity, DiscoveryClaim.discovery_entity_id == DiscoveryEntity.id)
            .where(DiscoveryEntity.catalogue_service_id == catalogue_id)
            .order_by(DiscoveryClaim.created_at.asc(), DiscoveryClaim.id.asc())
        )
        return list(self._session.scalars(stmt).all())

    def catalogue_claim_kinds_and_payloads(
        self, catalogue_id: UUID
    ) -> list[tuple[DiscoveryClaimKind, dict[str, object]]]:
        """Return the kind and payload of every claim of one catalogue row, unordered."""
        stmt = (
            select(DiscoveryClaim.kind, DiscoveryClaim.payload)
            .join(DiscoveryEntity, DiscoveryClaim.discovery_entity_id == DiscoveryEntity.id)
            .where(DiscoveryEntity.catalogue_service_id == catalogue_id)
        )
        return [(kind, payload) for kind, payload in self._session.execute(stmt).tuples().all()]
