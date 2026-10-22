"""Machine claim ingest: validate, append, advance the stage, record lineage."""

from __future__ import annotations

from decimal import Decimal

from pydantic import ValidationError

from app.features.discovery.claim_service import ClaimDraft, ClaimService
from app.features.discovery.errors import (
    DiscoveryEntityNotFoundError,
    InvalidDiscoveryInputError,
)
from app.features.discovery.repository import DiscoveryRepository, NewEvent
from app.features.discovery.stage_sync import advance_stage
from app.models.discovery import DiscoveryClaim, DiscoveryEntity, DiscoveryEventType
from app.schema.discovery.claim_payloads import validate_claim_payload
from app.schema.discovery.machine import ClaimAppendRequest, ClaimAppendResponse


def draft_from_request(body: ClaimAppendRequest) -> ClaimDraft:
    """Validate the payload and build a claim draft; raise on invalid payloads."""
    try:
        payload = validate_claim_payload(body.kind, body.payload)
    except ValidationError as err:
        raise InvalidDiscoveryInputError(str(err)) from err
    confidence = None if body.confidence is None else Decimal(str(body.confidence))
    return ClaimDraft(
        discovery_entity_id=body.discovery_entity_id,
        kind=body.kind,
        payload=payload,
        confidence=confidence,
    )


class ClaimIngest:
    """Append machine-submitted claims and keep the pipeline stage current."""

    def __init__(self, repository: DiscoveryRepository) -> None:
        """Bind the ingest to ``repository``."""
        self._repo = repository
        self._claims = ClaimService(repository)

    def append(self, body: ClaimAppendRequest) -> ClaimAppendResponse:
        """Append one claim; record a lineage event only when it is new."""
        entity = self._require_entity(body)
        draft = draft_from_request(body)
        row, created = self._claims.append_claim(draft)
        self._advance(entity)
        if created:
            self._repo.record_event(_claim_recorded(entity, row))
        return ClaimAppendResponse(id=row.id, discovery_entity_id=row.discovery_entity_id, kind=row.kind)

    def _require_entity(self, body: ClaimAppendRequest) -> DiscoveryEntity:
        entity = self._repo.get_entity(body.discovery_entity_id)
        if entity is None:
            raise DiscoveryEntityNotFoundError()
        return entity

    def _advance(self, entity: DiscoveryEntity) -> None:
        catalogue = self._repo.get_catalogue(entity.catalogue_service_id)
        if catalogue is not None:
            advance_stage(self._repo, catalogue)


def _claim_recorded(entity: DiscoveryEntity, row: DiscoveryClaim) -> NewEvent:
    return NewEvent(
        event_type=DiscoveryEventType.CLAIM_RECORDED,
        catalogue_service_id=entity.catalogue_service_id,
        payload={"claim_id": str(row.id), "kind": row.kind.value},
    )
