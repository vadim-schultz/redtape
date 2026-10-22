"""Emit staging claims as pending suggestions via ``SuggestionService``."""

from __future__ import annotations

from uuid import UUID

from app.features.discovery.emit_preview import claim_to_suggestion_payload
from app.features.discovery.lookups import require_catalogue
from app.features.discovery.repository import DiscoveryRepository, NewEvent
from app.features.suggestions.service import SubmitterRef, SuggestionService
from app.models.api_key import ApiKey
from app.models.discovery import DiscoveryClaim, DiscoveryEntity, DiscoveryEventType
from app.models.suggestion import SuggestionKind
from app.schema.discovery.machine import CatalogueEmitItemResult, CatalogueEmitResponse
from app.schema.suggestion.create import SuggestionCreate


def _idempotency_key_for_claim(claim_id: UUID) -> str:
    return f"discovery-emit:{claim_id}"


def _suggestion_create_from_body(body: dict[str, object]) -> SuggestionCreate:
    kind = SuggestionKind(str(body["kind"]))
    return SuggestionCreate.model_validate(
        {
            "kind": kind.value,
            "jurisdiction_id": body["jurisdiction_id"],
            "source_url": body["source_url"],
            "payload": body["payload"],
        }
    )


class DiscoveryEmitService:
    """Create pending suggestions from emit-ready staging claims."""

    def __init__(self, repository: DiscoveryRepository, suggestions: SuggestionService) -> None:
        self._repo = repository
        self._suggestions = suggestions

    def emit_catalogue(self, catalogue_id: UUID, *, api_key: ApiKey) -> CatalogueEmitResponse:
        row = require_catalogue(self._repo, catalogue_id)
        submitter = SubmitterRef("crawler", api_key.id)
        entities = self._repo.list_catalogue_entities(catalogue_id)
        entities_by_id = {entity.id: entity for entity in entities}
        claims = self._repo.list_catalogue_claims(catalogue_id)
        items, created_count, skipped_count, replayed_count = self._emit_claims(
            claims=claims,
            entities_by_id=entities_by_id,
            jurisdiction_id=row.jurisdiction_id,
            submitter=submitter,
        )
        self._repo.record_event(
            NewEvent(
                event_type=DiscoveryEventType.EMIT_ATTEMPTED,
                catalogue_service_id=catalogue_id,
                payload={
                    "created_count": created_count,
                    "skipped_count": skipped_count,
                    "replayed_count": replayed_count,
                    "claim_count": len(claims),
                },
            )
        )
        return CatalogueEmitResponse(
            items=items,
            created_count=created_count,
            skipped_count=skipped_count,
            replayed_count=replayed_count,
        )

    def _emit_claims(
        self,
        *,
        claims: list[DiscoveryClaim],
        entities_by_id: dict[UUID, DiscoveryEntity],
        jurisdiction_id: UUID,
        submitter: SubmitterRef,
    ) -> tuple[list[CatalogueEmitItemResult], int, int, int]:
        items: list[CatalogueEmitItemResult] = []
        created_count = 0
        skipped_count = 0
        replayed_count = 0
        for claim in claims:
            item = self._emit_one_claim(
                claim=claim,
                entities_by_id=entities_by_id,
                jurisdiction_id=jurisdiction_id,
                submitter=submitter,
            )
            items.append(item)
            if item.skip_reason is not None:
                skipped_count += 1
            elif item.replayed:
                replayed_count += 1
            else:
                created_count += 1
        return items, created_count, skipped_count, replayed_count

    def _emit_one_claim(
        self,
        *,
        claim: DiscoveryClaim,
        entities_by_id: dict[UUID, DiscoveryEntity],
        jurisdiction_id: UUID,
        submitter: SubmitterRef,
    ) -> CatalogueEmitItemResult:
        entity = entities_by_id.get(claim.discovery_entity_id)
        if entity is None:
            return CatalogueEmitItemResult(
                claim_id=claim.id,
                suggestion_id=None,
                skip_reason="missing_entity",
                replayed=False,
            )
        body, skip_reason = claim_to_suggestion_payload(
            claim=claim,
            entity=entity,
            jurisdiction_id=jurisdiction_id,
        )
        if skip_reason is not None or body is None:
            return CatalogueEmitItemResult(
                claim_id=claim.id,
                suggestion_id=None,
                skip_reason=skip_reason,
                replayed=False,
            )
        request = _suggestion_create_from_body(body)
        idempotency_key = _idempotency_key_for_claim(claim.id)
        result = self._suggestions.create(
            submitter=submitter,
            request=request,
            idempotency_key=idempotency_key,
        )
        return CatalogueEmitItemResult(
            claim_id=claim.id,
            suggestion_id=result.suggestion.id,
            skip_reason=None,
            replayed=result.replayed,
        )
