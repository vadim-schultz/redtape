"""Document candidate and mention persistence."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select

from app.features.discovery.repository.base import SessionRepository
from app.models.discovery import (
    DiscoveryCandidateMention,
    DiscoveryDocumentCandidate,
    DiscoveryMentionRole,
)
from app.models.jurisdiction import Jurisdiction


class CandidateRepository(SessionRepository):
    """Read and write document candidates and their mentions."""

    def get_candidate_by_key(self, *, jurisdiction_id: UUID, key: str) -> DiscoveryDocumentCandidate | None:
        """Return the candidate of ``jurisdiction_id`` with ``key``, if any."""
        stmt = select(DiscoveryDocumentCandidate).where(
            DiscoveryDocumentCandidate.jurisdiction_id == jurisdiction_id,
            DiscoveryDocumentCandidate.key == key,
        )
        return self._session.scalar(stmt)

    def get_jurisdiction_name_i18n(self, jurisdiction_id: UUID) -> dict[str, str]:
        """Return the localized names of ``jurisdiction_id``, empty when it is gone."""
        stmt = select(Jurisdiction.name_i18n).where(Jurisdiction.id == jurisdiction_id)
        return self._session.scalar(stmt) or {}

    def add_candidate(self, candidate: DiscoveryDocumentCandidate) -> DiscoveryDocumentCandidate:
        """Add ``candidate`` to the session and flush it."""
        self._session.add(candidate)
        self._session.flush()
        return candidate

    def find_mention(
        self, *, candidate_id: UUID, catalogue_service_id: UUID, role: DiscoveryMentionRole, source_field: str
    ) -> DiscoveryCandidateMention | None:
        """Return the mention with this unique key, if any."""
        stmt = select(DiscoveryCandidateMention).where(
            DiscoveryCandidateMention.candidate_id == candidate_id,
            DiscoveryCandidateMention.catalogue_service_id == catalogue_service_id,
            DiscoveryCandidateMention.role == role,
            DiscoveryCandidateMention.source_field == source_field,
        )
        return self._session.scalar(stmt)

    def add_mention(self, mention: DiscoveryCandidateMention) -> DiscoveryCandidateMention:
        """Add ``mention`` to the session and flush it."""
        self._session.add(mention)
        self._session.flush()
        return mention

    def candidate_ids_by_catalogue(self, catalogue_ids: Sequence[UUID]) -> dict[UUID, tuple[UUID, ...]]:
        """Return the candidates each catalogue row in ``catalogue_ids`` is mentioned by; rows without any are absent."""
        stmt = (
            select(DiscoveryCandidateMention.catalogue_service_id, DiscoveryCandidateMention.candidate_id)
            .where(DiscoveryCandidateMention.catalogue_service_id.in_(catalogue_ids))
            .distinct()
            .order_by(DiscoveryCandidateMention.catalogue_service_id, DiscoveryCandidateMention.candidate_id)
        )
        grouped: dict[UUID, list[UUID]] = defaultdict(list)
        for catalogue_id, candidate_id in self._session.execute(stmt).tuples():
            grouped[catalogue_id].append(candidate_id)
        return {catalogue_id: tuple(candidates) for catalogue_id, candidates in grouped.items()}
