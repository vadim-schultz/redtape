"""Upsert policy for document candidates and their mentions."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.features.discovery.candidate_key import candidate_key
from app.features.discovery.lookups import require_catalogue
from app.features.discovery.repository import DiscoveryRepository
from app.models.discovery import DiscoveryCandidateMention, DiscoveryDocumentCandidate
from app.schema.discovery.candidates import (
    CandidateMentionItem,
    CandidateMentionsRequest,
    CandidateMentionsResponse,
)


@dataclass(frozen=True, slots=True)
class MentionOutcome:
    """Whether recording one item created its candidate and its mention."""

    candidate_created: bool
    mention_created: bool


def merge_titles(existing: dict[str, str], incoming: dict[str, str]) -> dict[str, str]:
    """Return ``existing`` plus the non-blank ``incoming`` locales it lacks."""
    additions = {locale: text for locale, text in incoming.items() if text.strip() and locale not in existing}
    return {**existing, **additions}


def _new_mention(candidate: DiscoveryDocumentCandidate, item: CandidateMentionItem) -> DiscoveryCandidateMention:
    return DiscoveryCandidateMention(
        candidate_id=candidate.id,
        catalogue_service_id=item.catalogue_service_id,
        role=item.role,
        source_field=item.source_field,
        excerpt=item.excerpt,
        artifact_id=item.artifact_id,
        extractor=item.extractor,
        extractor_version=item.extractor_version,
    )


def _refresh_mention(mention: DiscoveryCandidateMention, item: CandidateMentionItem) -> None:
    mention.excerpt = item.excerpt
    mention.extractor = item.extractor
    mention.extractor_version = item.extractor_version
    mention.artifact_id = item.artifact_id or mention.artifact_id


def _tally(outcomes: list[MentionOutcome]) -> CandidateMentionsResponse:
    mentions_created = sum(outcome.mention_created for outcome in outcomes)
    return CandidateMentionsResponse(
        candidates_created=sum(outcome.candidate_created for outcome in outcomes),
        mentions_created=mentions_created,
        mentions_updated=len(outcomes) - mentions_created,
    )


class CandidateService:
    """Record mentions and keep one candidate per jurisdiction and key."""

    def __init__(self, repository: DiscoveryRepository) -> None:
        """Bind the service to ``repository``."""
        self._repo = repository

    def record_mentions(self, body: CandidateMentionsRequest) -> CandidateMentionsResponse:
        """Record every item or none: lookups and keys are checked before the first write."""
        jurisdictions = self._jurisdictions(body.items)
        keyed = [(item, candidate_key(item.title_i18n)) for item in body.items]
        return _tally([self._record(item, key, jurisdictions[item.catalogue_service_id]) for item, key in keyed])

    def _jurisdictions(self, items: list[CandidateMentionItem]) -> dict[UUID, UUID]:
        ids = {item.catalogue_service_id for item in items}
        return {catalogue_id: require_catalogue(self._repo, catalogue_id).jurisdiction_id for catalogue_id in ids}

    def _record(self, item: CandidateMentionItem, key: str, jurisdiction_id: UUID) -> MentionOutcome:
        candidate, candidate_created = self._resolve_candidate(item, key, jurisdiction_id)
        return MentionOutcome(candidate_created, self._upsert_mention(candidate, item))

    def _resolve_candidate(
        self, item: CandidateMentionItem, key: str, jurisdiction_id: UUID
    ) -> tuple[DiscoveryDocumentCandidate, bool]:
        candidate = self._repo.get_candidate_by_key(jurisdiction_id=jurisdiction_id, key=key)
        if candidate is None:
            return self._repo.add_candidate(self._new_candidate(item, key, jurisdiction_id)), True
        self._merge_fields(candidate, item)
        return candidate, False

    def _new_candidate(self, item: CandidateMentionItem, key: str, jurisdiction_id: UUID) -> DiscoveryDocumentCandidate:
        return DiscoveryDocumentCandidate(
            jurisdiction_id=jurisdiction_id,
            key=key,
            title_i18n=merge_titles({}, item.title_i18n),
            official_url=item.official_url,
        )

    def _merge_fields(self, candidate: DiscoveryDocumentCandidate, item: CandidateMentionItem) -> None:
        candidate.title_i18n = merge_titles(candidate.title_i18n, item.title_i18n)
        candidate.official_url = candidate.official_url or item.official_url
        self._repo.flush()

    def _upsert_mention(self, candidate: DiscoveryDocumentCandidate, item: CandidateMentionItem) -> bool:
        mention = self._find_mention(candidate, item)
        if mention is not None:
            _refresh_mention(mention, item)
            self._repo.flush()
            return False
        self._repo.add_mention(_new_mention(candidate, item))
        return True

    def _find_mention(
        self, candidate: DiscoveryDocumentCandidate, item: CandidateMentionItem
    ) -> DiscoveryCandidateMention | None:
        return self._repo.find_mention(
            candidate_id=candidate.id,
            catalogue_service_id=item.catalogue_service_id,
            role=item.role,
            source_field=item.source_field,
        )
