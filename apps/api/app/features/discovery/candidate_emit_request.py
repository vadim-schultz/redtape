"""Build the suggestion request that emits a document candidate."""

from __future__ import annotations

from collections.abc import Callable

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.features.discovery.candidate_emit_payload import SuggestedTags, new_document_payload
from app.features.discovery.candidate_emit_skip import EmitSkip
from app.features.discovery.repository import DiscoveryRepository
from app.models.discovery import DiscoveryDocumentCandidate
from app.schema.discovery.emit import SkipReason
from app.schema.suggestion.create import SuggestionCreate

TagHook = Callable[[Session, DiscoveryDocumentCandidate], SuggestedTags]


class CandidateRequestBuilder:
    """Turn a candidate into a ``new_document`` request sourced from its first mentioned procedure."""

    def __init__(self, repository: DiscoveryRepository, tags: TagHook) -> None:
        """Bind the builder to ``repository`` and the ``tags`` hook."""
        self._repo = repository
        self._tags = tags

    def build(self, candidate: DiscoveryDocumentCandidate) -> SuggestionCreate:
        """Return the request for ``candidate`` or raise :exc:`EmitSkip` when it cannot form one."""
        body = {
            "kind": "new_document",
            "jurisdiction_id": candidate.jurisdiction_id,
            "source_url": self._source_url(candidate),
            "payload": new_document_payload(candidate, self._tags(self._repo.session, candidate)),
        }
        try:
            return SuggestionCreate.model_validate(body)
        except ValidationError as exc:
            raise EmitSkip(SkipReason.INVALID_PAYLOAD) from exc

    def _source_url(self, candidate: DiscoveryDocumentCandidate) -> str:
        mentions = self._repo.list_candidate_mentions(candidate.id)
        if not mentions:
            raise EmitSkip(SkipReason.NO_MENTIONS)
        portal_url = mentions[0].procedure.portal_url
        if portal_url is None:
            raise EmitSkip(SkipReason.NO_SOURCE_URL)
        return portal_url
