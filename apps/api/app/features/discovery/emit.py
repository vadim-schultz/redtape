"""Emit staging claims as pending suggestions via ``SuggestionService``."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from pydantic import ValidationError

from app.features.discovery.candidate_emit_skip import EmitSkip
from app.features.discovery.emit_preview import claim_to_suggestion_payload
from app.features.discovery.emit_submit import idempotency_key, submit_or_skip
from app.features.discovery.lookups import require_catalogue
from app.features.discovery.repository import DiscoveryRepository, NewEvent
from app.features.suggestions.service import SuggestionService
from app.features.suggestions.submitters import CrawlerSubmitter, Submitter
from app.models.api_key import ApiKey
from app.models.discovery import DiscoveryClaim, DiscoveryEntity, DiscoveryEventType
from app.models.suggestion import SuggestionKind
from app.schema.discovery.emit import SkipReason, tally_outcomes
from app.schema.discovery.machine import CatalogueEmitItemResult, CatalogueEmitResponse
from app.schema.suggestion.create import SuggestionCreate


def _suggestion_create_from_body(body: dict[str, object]) -> SuggestionCreate:
    """Validate ``body`` into a ``SuggestionCreate``, or raise ``EmitSkip`` when it does not validate."""
    kind = SuggestionKind(str(body["kind"]))
    try:
        return SuggestionCreate.model_validate(
            {
                "kind": kind.value,
                "jurisdiction_id": body["jurisdiction_id"],
                "source_url": body["source_url"],
                "payload": body["payload"],
            }
        )
    except ValidationError as exc:
        raise EmitSkip(SkipReason.INVALID_PAYLOAD) from exc


@dataclass(frozen=True, slots=True)
class _EmitContext:
    """Per-run inputs shared by every claim in one emit."""

    entities_by_id: dict[UUID, DiscoveryEntity]
    jurisdiction_id: UUID
    submitter: Submitter


def _skipped(claim: DiscoveryClaim, reason: SkipReason | None) -> CatalogueEmitItemResult:
    return CatalogueEmitItemResult(claim_id=claim.id, suggestion_id=None, skip_reason=reason, replayed=False)


def _tally(items: list[CatalogueEmitItemResult]) -> CatalogueEmitResponse:
    return CatalogueEmitResponse(items=items, **tally_outcomes(items).model_dump())


def _attempt_event(catalogue_id: UUID, response: CatalogueEmitResponse, claim_count: int) -> NewEvent:
    return NewEvent(
        event_type=DiscoveryEventType.EMIT_ATTEMPTED,
        catalogue_service_id=catalogue_id,
        payload={
            "created_count": response.created_count,
            "skipped_count": response.skipped_count,
            "replayed_count": response.replayed_count,
            "claim_count": claim_count,
        },
    )


class DiscoveryEmitService:
    """Create pending suggestions from emit-ready staging claims."""

    def __init__(self, repository: DiscoveryRepository, suggestions: SuggestionService) -> None:
        """Bind the service to its repository and the suggestion service."""
        self._repo = repository
        self._suggestions = suggestions

    def emit_catalogue(self, catalogue_id: UUID, *, api_key: ApiKey) -> CatalogueEmitResponse:
        """Emit every claim of a catalogue row and record the attempt."""
        row = require_catalogue(self._repo, catalogue_id)
        entities = self._repo.list_catalogue_entities(catalogue_id)
        context = _EmitContext({e.id: e for e in entities}, row.jurisdiction_id, CrawlerSubmitter(api_key.id))
        claims = self._repo.list_catalogue_claims(catalogue_id)
        response = _tally([self._emit_one_claim(claim, context) for claim in claims])
        self._repo.record_event(_attempt_event(catalogue_id, response, len(claims)))
        return response

    def _emit_one_claim(self, claim: DiscoveryClaim, context: _EmitContext) -> CatalogueEmitItemResult:
        entity = context.entities_by_id.get(claim.discovery_entity_id)
        if entity is None:
            return _skipped(claim, SkipReason.MISSING_ENTITY)
        body, skip_reason = claim_to_suggestion_payload(
            claim=claim, entity=entity, jurisdiction_id=context.jurisdiction_id
        )
        if skip_reason is not None or body is None:
            return _skipped(claim, skip_reason)
        try:
            return self._create(claim, body, context.submitter)
        except EmitSkip as skip:
            return _skipped(claim, skip.reason)

    def _create(self, claim: DiscoveryClaim, body: dict[str, object], submitter: Submitter) -> CatalogueEmitItemResult:
        request = _suggestion_create_from_body(body)
        result = submit_or_skip(
            self._suggestions,
            submitter=submitter,
            request=request,
            idempotency_key=idempotency_key("emit", claim.id),
        )
        return CatalogueEmitItemResult(
            claim_id=claim.id,
            suggestion_id=result.suggestion.id,
            skip_reason=None,
            replayed=result.replayed,
        )
