"""Claim append policy: fingerprinting, upsert and lost-race recovery."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.features.discovery.claim_fingerprint import claim_payload_fingerprint
from app.features.discovery.repository import DiscoveryRepository
from app.models.discovery import DiscoveryClaim, DiscoveryClaimKind


@dataclass(frozen=True, slots=True)
class ClaimDraft:
    """A validated claim ready to be appended to an entity."""

    discovery_entity_id: UUID
    kind: DiscoveryClaimKind
    payload: dict[str, object]
    confidence: Decimal | None


class ClaimService:
    """Append claims idempotently, keyed by payload fingerprint."""

    def __init__(self, repository: DiscoveryRepository) -> None:
        """Bind the service to ``repository``."""
        self._repo = repository

    def append_claim(self, draft: ClaimDraft) -> tuple[DiscoveryClaim, bool]:
        """Insert or update a claim keyed by payload fingerprint; return ``(row, created)``."""
        fingerprint = claim_payload_fingerprint(draft.kind, draft.payload)
        existing = self._find(draft, fingerprint)
        if existing is not None:
            return self._refresh(existing, draft), False
        return self._insert_or_recover(draft, fingerprint)

    def _find(self, draft: ClaimDraft, fingerprint: str) -> DiscoveryClaim | None:
        return self._repo.find_claim_by_fingerprint(
            discovery_entity_id=draft.discovery_entity_id,
            kind=draft.kind,
            payload_fingerprint=fingerprint,
        )

    def _insert_or_recover(self, draft: ClaimDraft, fingerprint: str) -> tuple[DiscoveryClaim, bool]:
        row = _new_row(draft, fingerprint)
        try:
            self._repo.add_claim(row)
        except IntegrityError as exc:
            return self._recover(draft, fingerprint, exc), False
        return row, True

    def _recover(self, draft: ClaimDraft, fingerprint: str, exc: IntegrityError) -> DiscoveryClaim:
        self._repo.rollback()
        raced = self._find(draft, fingerprint)
        if raced is None:
            raise exc
        return self._refresh(raced, draft)

    def _refresh(self, row: DiscoveryClaim, draft: ClaimDraft) -> DiscoveryClaim:
        row.payload = draft.payload
        row.confidence = draft.confidence
        self._repo.flush()
        return row


def _new_row(draft: ClaimDraft, fingerprint: str) -> DiscoveryClaim:
    return DiscoveryClaim(
        discovery_entity_id=draft.discovery_entity_id,
        kind=draft.kind,
        payload=draft.payload,
        payload_fingerprint=fingerprint,
        confidence=draft.confidence,
    )
