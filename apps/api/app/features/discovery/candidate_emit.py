"""Emit staged document candidates as pending ``new_document`` suggestions."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from pydantic import ValidationError

from app.features.discovery.candidate_emit_payload import SuggestedTags, new_document_payload, suggested_tags
from app.features.discovery.candidate_emit_skip import EmitSkip
from app.features.discovery.lookups import require_candidate
from app.features.discovery.repository import DiscoveryRepository
from app.features.suggestions.service import (
    DuplicateSuggestionError,
    SubmissionResult,
    SubmitterRef,
    SuggestionService,
    UnknownTaxonomyCodeError,
)
from app.models.api_key import ApiKey
from app.models.discovery import DiscoveryCandidateStatus, DiscoveryDocumentCandidate
from app.schema.discovery.candidate_emit import (
    CandidateEmitItemResult,
    CandidateEmitPreview,
    CandidateEmitResponse,
    EmitConflictRead,
)
from app.schema.suggestion.create import SuggestionCreate

TagHook = Callable[[DiscoveryDocumentCandidate], SuggestedTags]


def _idempotency_key(candidate_id: UUID) -> str:
    return f"discovery-candidate-emit:{candidate_id}"


def _conflict_reads(skip: EmitSkip) -> list[EmitConflictRead]:
    return [EmitConflictRead(type=conflict.type, id=conflict.id) for conflict in skip.conflicts]


def _skipped(candidate_id: UUID, skip: EmitSkip) -> CandidateEmitItemResult:
    return CandidateEmitItemResult(candidate_id=candidate_id, skip_reason=skip.reason, conflicts=_conflict_reads(skip))


def _tally(items: list[CandidateEmitItemResult]) -> CandidateEmitResponse:
    skipped = sum(item.skip_reason is not None for item in items)
    replayed = sum(item.skip_reason is None and item.replayed for item in items)
    return CandidateEmitResponse(
        items=items, created_count=len(items) - skipped - replayed, skipped_count=skipped, replayed_count=replayed
    )


class DiscoveryCandidateEmitService:
    """Turn reviewed candidates into pending suggestions, one deliberate call at a time."""

    def __init__(
        self,
        repository: DiscoveryRepository,
        suggestions: SuggestionService,
        tags: TagHook = suggested_tags,
    ) -> None:
        """Bind the service to its repository, the suggestion service and the tag hook."""
        self._repo = repository
        self._suggestions = suggestions
        self._tags = tags

    def emit_batch(self, candidate_ids: list[UUID], api_key: ApiKey) -> CandidateEmitResponse:
        """Emit every candidate and total the outcomes."""
        return _tally([self.emit(candidate_id, api_key) for candidate_id in candidate_ids])

    def emit(self, candidate_id: UUID, api_key: ApiKey) -> CandidateEmitItemResult:
        """Emit one candidate; an unknown or unemittable one is a reported skip."""
        candidate = self._repo.get_candidate(candidate_id)
        if candidate is None:
            return _skipped(candidate_id, EmitSkip("not_found"))
        try:
            return self._emit(candidate, api_key)
        except EmitSkip as skip:
            return _skipped(candidate_id, skip)

    def preview(self, candidate_id: UUID) -> CandidateEmitPreview:
        """Return what ``emit`` would create for the candidate, without writing."""
        candidate = require_candidate(self._repo, candidate_id)
        try:
            return CandidateEmitPreview(candidate_id=candidate_id, suggestion=self._previewed_request(candidate))
        except EmitSkip as skip:
            return CandidateEmitPreview(
                candidate_id=candidate_id,
                suggestion_id=candidate.suggestion_id,
                skip_reason=skip.reason,
                conflicts=_conflict_reads(skip),
            )

    def _emit(self, candidate: DiscoveryDocumentCandidate, api_key: ApiKey) -> CandidateEmitItemResult:
        if candidate.status == DiscoveryCandidateStatus.EMITTED:
            return CandidateEmitItemResult(
                candidate_id=candidate.id, suggestion_id=candidate.suggestion_id, replayed=True
            )
        result = self._create(candidate, api_key)
        candidate.status = DiscoveryCandidateStatus.EMITTED
        candidate.suggestion_id = result.suggestion.id
        self._repo.flush()
        return CandidateEmitItemResult(
            candidate_id=candidate.id, suggestion_id=result.suggestion.id, replayed=result.replayed
        )

    def _create(self, candidate: DiscoveryDocumentCandidate, api_key: ApiKey) -> SubmissionResult:
        try:
            return self._suggestions.create(
                submitter=SubmitterRef("crawler", api_key.id),
                request=self._request(candidate),
                idempotency_key=_idempotency_key(candidate.id),
            )
        except DuplicateSuggestionError as exc:
            raise EmitSkip("duplicate", exc.conflicts) from exc
        except UnknownTaxonomyCodeError as exc:
            raise EmitSkip("invalid_payload") from exc

    def _previewed_request(self, candidate: DiscoveryDocumentCandidate) -> SuggestionCreate:
        if candidate.status == DiscoveryCandidateStatus.EMITTED:
            raise EmitSkip("already_emitted")
        request = self._request(candidate)
        try:
            conflicts = self._suggestions.preview_conflicts(request)
        except UnknownTaxonomyCodeError as exc:
            raise EmitSkip("invalid_payload") from exc
        if conflicts:
            raise EmitSkip("duplicate", conflicts)
        return request

    def _request(self, candidate: DiscoveryDocumentCandidate) -> SuggestionCreate:
        body = {
            "kind": "new_document",
            "jurisdiction_id": candidate.jurisdiction_id,
            "source_url": self._source_url(candidate),
            "payload": new_document_payload(candidate, self._tags(candidate)),
        }
        try:
            return SuggestionCreate.model_validate(body)
        except ValidationError as exc:
            raise EmitSkip("invalid_payload") from exc

    def _source_url(self, candidate: DiscoveryDocumentCandidate) -> str:
        mentions = self._repo.list_candidate_mentions(candidate.id)
        if not mentions:
            raise EmitSkip("no_mentions")
        portal_url = mentions[0][1].portal_url
        if portal_url is None:
            raise EmitSkip("no_source_url")
        return portal_url
