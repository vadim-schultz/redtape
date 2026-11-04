"""Emit staged document candidates as pending ``new_document`` suggestions."""

from __future__ import annotations

from uuid import UUID

from app.features.discovery.candidate_emit_payload import suggested_tags
from app.features.discovery.candidate_emit_request import CandidateRequestBuilder, TagHook
from app.features.discovery.candidate_emit_results import conflict_reads, emitted, skipped, tally
from app.features.discovery.candidate_emit_skip import EmitSkip
from app.features.discovery.emit_submit import SUGGESTION_RULE_REASONS, idempotency_key, submit_or_skip
from app.features.discovery.lookups import require_candidate
from app.features.discovery.repository import DiscoveryRepository
from app.features.suggestions.service import (
    SubmissionResult,
    SuggestionService,
    UnknownTaxonomyCodeError,
)
from app.features.suggestions.submitters import CrawlerSubmitter
from app.models.api_key import ApiKey
from app.models.discovery import DiscoveryCandidateStatus, DiscoveryDocumentCandidate
from app.schema.discovery.candidate_emit import (
    CandidateEmitItemResult,
    CandidateEmitPreview,
    CandidateEmitResponse,
)
from app.schema.discovery.emit import SkipReason
from app.schema.suggestion.create import SuggestionCreate


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
        self._requests = CandidateRequestBuilder(repository, tags)

    def emit_batch(self, candidate_ids: list[UUID], api_key: ApiKey) -> CandidateEmitResponse:
        """Emit every candidate and total the outcomes."""
        return tally([self.emit(candidate_id, api_key) for candidate_id in candidate_ids])

    def emit(self, candidate_id: UUID, api_key: ApiKey) -> CandidateEmitItemResult:
        """Emit one candidate; an unknown or unemittable one is a reported skip."""
        candidate = self._repo.get_candidate(candidate_id)
        if candidate is None:
            return skipped(candidate_id, EmitSkip(SkipReason.NOT_FOUND))
        try:
            return self._emit(candidate, api_key)
        except EmitSkip as skip:
            return skipped(candidate_id, skip)

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
                conflicts=conflict_reads(skip),
            )

    def _emit(self, candidate: DiscoveryDocumentCandidate, api_key: ApiKey) -> CandidateEmitItemResult:
        if candidate.status == DiscoveryCandidateStatus.EMITTED:
            return emitted(candidate.id, candidate.suggestion_id, replayed=True)
        result = self._create(candidate, api_key)
        self._mark_emitted(candidate, result.suggestion.id)
        return emitted(candidate.id, result.suggestion.id, replayed=result.replayed)

    def _mark_emitted(self, candidate: DiscoveryDocumentCandidate, suggestion_id: UUID) -> None:
        candidate.status = DiscoveryCandidateStatus.EMITTED
        candidate.suggestion_id = suggestion_id
        self._repo.flush()

    def _create(self, candidate: DiscoveryDocumentCandidate, api_key: ApiKey) -> SubmissionResult:
        return submit_or_skip(
            self._suggestions,
            submitter=CrawlerSubmitter(api_key.id),
            request=self._requests.build(candidate),
            idempotency_key=idempotency_key("candidate-emit", candidate.id),
        )

    def _previewed_request(self, candidate: DiscoveryDocumentCandidate) -> SuggestionCreate:
        if candidate.status == DiscoveryCandidateStatus.EMITTED:
            raise EmitSkip(SkipReason.ALREADY_EMITTED)
        request = self._requests.build(candidate)
        try:
            conflicts = self._suggestions.preview_conflicts(request)
        except UnknownTaxonomyCodeError as exc:
            raise EmitSkip(SUGGESTION_RULE_REASONS[UnknownTaxonomyCodeError]) from exc
        if conflicts:
            raise EmitSkip(SkipReason.DUPLICATE, conflicts)
        return request
