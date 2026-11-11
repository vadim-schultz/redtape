"""Upsert policy for document candidates and their mentions."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.features.discovery.candidate_codes import CodeVocabulary
from app.features.discovery.candidate_key import candidate_key
from app.features.discovery.lookups import require_catalogue
from app.features.discovery.mention_rows import PreparedMention, new_mention, refresh_mention
from app.features.discovery.repository import DiscoveryRepository
from app.features.search.service import SearchTextService
from app.features.taxonomy.service import TaxonomyService
from app.features.translation.enqueue import TranslationEnqueuer
from app.models.discovery import DiscoveryCandidateMention, DiscoveryDocumentCandidate
from app.schema.discovery.candidates import (
    CandidateMentionItem,
    CandidateMentionsRequest,
    CandidateMentionsResponse,
)


@dataclass(frozen=True, slots=True)
class MentionOutcome:
    """Whether recording one item created its candidate and its mention."""

    candidate_id: UUID
    candidate_created: bool
    mention_created: bool


def merge_titles(existing: dict[str, str], incoming: dict[str, str]) -> dict[str, str]:
    """Return ``existing`` plus the non-blank ``incoming`` locales it lacks."""
    additions = {locale: text for locale, text in incoming.items() if text.strip() and locale not in existing}
    return {**existing, **additions}


def _tally(prepared: list[PreparedMention], outcomes: list[MentionOutcome]) -> CandidateMentionsResponse:
    mentions_created = sum(outcome.mention_created for outcome in outcomes)
    return CandidateMentionsResponse(
        candidates_created=sum(outcome.candidate_created for outcome in outcomes),
        mentions_created=mentions_created,
        mentions_updated=len(outcomes) - mentions_created,
        unknown_codes=sum(entry.codes.dropped for entry in prepared),
    )


class CandidateService:
    """Record mentions and keep one candidate per jurisdiction and key."""

    def __init__(
        self,
        repository: DiscoveryRepository,
        taxonomy: TaxonomyService,
        search_text: SearchTextService,
        translation: TranslationEnqueuer,
    ) -> None:
        """Bind to ``repository``, the ``taxonomy`` that vets codes, the ``search_text`` kept current and ``translation``."""
        self._repo = repository
        self._taxonomy = taxonomy
        self._search_text = search_text
        self._translation = translation

    def record_mentions(self, body: CandidateMentionsRequest) -> CandidateMentionsResponse:
        """Record every item or none: lookups and keys are checked before the first write."""
        prepared = self._prepare(body.items)
        outcomes = [self._record(entry) for entry in prepared]
        candidate_ids = sorted({outcome.candidate_id for outcome in outcomes})
        self._search_text.refresh_many(candidate_ids)
        self._translation.enqueue_many(candidate_ids)
        return _tally(prepared, outcomes)

    def _prepare(self, items: list[CandidateMentionItem]) -> list[PreparedMention]:
        jurisdictions = self._jurisdictions(items)
        vocabulary = CodeVocabulary.for_items(items, self._taxonomy)
        return [
            PreparedMention(
                item, candidate_key(item.title_i18n), jurisdictions[item.catalogue_service_id], vocabulary.filter(item)
            )
            for item in items
        ]

    def _jurisdictions(self, items: list[CandidateMentionItem]) -> dict[UUID, UUID]:
        ids = {item.catalogue_service_id for item in items}
        return {catalogue_id: require_catalogue(self._repo, catalogue_id).jurisdiction_id for catalogue_id in ids}

    def _record(self, prepared: PreparedMention) -> MentionOutcome:
        candidate, candidate_created = self._resolve_candidate(prepared)
        return MentionOutcome(candidate.id, candidate_created, self._upsert_mention(candidate, prepared))

    def _resolve_candidate(self, prepared: PreparedMention) -> tuple[DiscoveryDocumentCandidate, bool]:
        candidate = self._repo.get_candidate_by_key(jurisdiction_id=prepared.jurisdiction_id, key=prepared.key)
        if candidate is None:
            return self._repo.add_candidate(self._new_candidate(prepared)), True
        self._merge_fields(candidate, prepared.item)
        return candidate, False

    def _new_candidate(self, prepared: PreparedMention) -> DiscoveryDocumentCandidate:
        return DiscoveryDocumentCandidate(
            jurisdiction_id=prepared.jurisdiction_id,
            key=prepared.key,
            title_i18n=merge_titles({}, prepared.item.title_i18n),
            official_url=prepared.item.official_url,
        )

    def _merge_fields(self, candidate: DiscoveryDocumentCandidate, item: CandidateMentionItem) -> None:
        candidate.title_i18n = merge_titles(candidate.title_i18n, item.title_i18n)
        candidate.official_url = candidate.official_url or item.official_url
        self._repo.flush()

    def _upsert_mention(self, candidate: DiscoveryDocumentCandidate, prepared: PreparedMention) -> bool:
        mention = self._find_mention(candidate, prepared.item)
        if mention is not None:
            refresh_mention(mention, prepared)
            self._repo.flush()
            return False
        self._repo.add_mention(new_mention(candidate, prepared))
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
