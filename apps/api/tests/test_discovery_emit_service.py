"""Service-level characterisation and behaviour tests for ``DiscoveryEmitService`` (chapter A2).

Pins the idempotency-key formats and skip-reason strings before the shared ``submit_or_skip``
pipeline lands, then exercises the claim-emit failure branches that used to abort the whole
catalogue batch (C2).
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from app.features.discovery.candidate_emit_skip import EmitSkip
from app.features.discovery.emit import DiscoveryEmitService
from app.features.discovery.emit_submit import SUGGESTION_RULE_REASONS, idempotency_key, submit_or_skip
from app.features.discovery.repository import DiscoveryRepository
from app.features.documents.promotion import DocumentPromotion
from app.features.documents.repository import DocumentRepository
from app.features.events.repository import EventLogRepository
from app.features.events.service import EventLogService
from app.features.suggestions.repository import SuggestionRepository
from app.features.suggestions.service import (
    CycleError,
    DuplicateSuggestionError,
    MissingSourceUrlError,
    UnknownDocumentError,
    UnknownJurisdictionError,
    UnknownTaxonomyCodeError,
)
from app.features.suggestions.submitters import CrawlerSubmitter
from app.features.taxonomy.repository import TaxonomyRepository
from app.features.taxonomy.service import TaxonomyService
from app.models.api_key import ApiKey
from app.models.discovery import CatalogueService, DiscoveryClaim, DiscoveryClaimKind, DiscoveryEntity, DiscoveryEvent
from app.models.document import Document
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.suggestion import Suggestion, SuggestionKind, SuggestionSource, SuggestionStatus
from app.schema.discovery.emit import SkipReason
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from suggestion_support import compose_suggestion_service
from test_discovery_admin_api import _catalogue


def _service(db_session: Session) -> DiscoveryEmitService:
    taxonomy = TaxonomyService(TaxonomyRepository(db_session))
    documents = DocumentPromotion(DocumentRepository(db_session))
    events = EventLogService(EventLogRepository(db_session))
    suggestions = compose_suggestion_service(SuggestionRepository(db_session), documents, taxonomy, events)
    return DiscoveryEmitService(DiscoveryRepository(db_session), suggestions)


def _api_key(db_session: Session) -> ApiKey:
    row = ApiKey(name="crawler", key_hash=uuid.uuid4().hex, key_prefix=uuid.uuid4().hex[:8])
    db_session.add(row)
    db_session.flush()
    return row


def _entity(
    db_session: Session, catalogue: CatalogueService, *, url: str = "https://example.gov/doc"
) -> DiscoveryEntity:
    entity = DiscoveryEntity(catalogue_service_id=catalogue.id, canonical_url=url, label="Doc")
    db_session.add(entity)
    db_session.flush()
    return entity


def _claim(
    db_session: Session,
    entity: DiscoveryEntity,
    *,
    kind: DiscoveryClaimKind,
    payload: dict[str, object],
) -> DiscoveryClaim:
    claim = DiscoveryClaim(
        discovery_entity_id=entity.id, kind=kind, payload=payload, payload_fingerprint=f"fp-{uuid.uuid4().hex}"
    )
    db_session.add(claim)
    db_session.flush()
    return claim


def _new_document_claim(
    db_session: Session,
    catalogue: CatalogueService,
    *,
    url: str = "https://example.gov/doc",
    title: str = "Ausweis",
    category_codes: list[str] | None = None,
    entity: DiscoveryEntity | None = None,
) -> DiscoveryClaim:
    entity = entity or _entity(db_session, catalogue, url=url)
    payload: dict[str, object] = {"title_i18n": {"de": title}, "official_url": url}
    if category_codes is not None:
        payload["category_codes"] = category_codes
    return _claim(db_session, entity, kind=DiscoveryClaimKind.NEW_DOCUMENT, payload=payload)


def _requirement_claim(
    db_session: Session, catalogue: CatalogueService, *, parent_id: uuid.UUID, required_id: uuid.UUID
) -> DiscoveryClaim:
    entity = _entity(db_session, catalogue, url="https://example.gov/req")
    payload = {"parent_document_id": str(parent_id), "required_document_id": str(required_id)}
    return _claim(db_session, entity, kind=DiscoveryClaimKind.NEW_REQUIREMENT, payload=payload)


def _count(db_session: Session, model: type) -> int:
    return int(db_session.scalar(select(func.count()).select_from(model)) or 0)


# --- Characterise first (pin today's behaviour before any production change) -----------------


def test_emit_catalogue_creates_one_pending_suggestion_per_emit_ready_claim(db_session: Session) -> None:
    catalogue = _catalogue(db_session)
    _new_document_claim(db_session, catalogue, url="https://example.gov/a", title="A")
    _new_document_claim(db_session, catalogue, url="https://example.gov/b", title="B")

    response = _service(db_session).emit_catalogue(catalogue.id, api_key=_api_key(db_session))

    assert (response.created_count, response.skipped_count, response.replayed_count) == (2, 0, 0)
    assert _count(db_session, Suggestion) == 2


def test_emit_catalogue_keeps_earlier_suggestions_when_a_later_insert_hits_integrity_error(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    catalogue = _catalogue(db_session)
    first = _new_document_claim(db_session, catalogue, url="https://example.gov/first", title="First")
    later = _new_document_claim(db_session, catalogue, url="https://example.gov/later", title="Later")
    # Both claims share one transaction timestamp, so emit order would fall back to random UUIDs.
    later.created_at = first.created_at + timedelta(seconds=1)
    db_session.flush()
    api_key = _api_key(db_session)
    replay = Suggestion(
        kind=SuggestionKind.NEW_DOCUMENT,
        status=SuggestionStatus.PENDING,
        source_type=SuggestionSource.CRAWLER,
        jurisdiction_id=catalogue.jurisdiction_id,
        payload={"title_i18n": {"de": "Already committed"}, "official_url": "https://example.gov/existing"},
        source_url="https://example.gov/existing",
        normalized_url="https://example.gov/existing",
        submitted_by_api_key_id=api_key.id,
        idempotency_key=f"discovery-emit:{later.id}",
    )
    db_session.add(replay)
    db_session.flush()
    db_session.commit()

    hidden_once = True
    real_find_replay = CrawlerSubmitter.find_replay

    def hide_later_replay_once(
        submitter: CrawlerSubmitter, repository: SuggestionRepository, key: str | None
    ) -> Suggestion | None:
        nonlocal hidden_once
        if key == replay.idempotency_key and hidden_once:
            hidden_once = False
            return None
        return real_find_replay(submitter, repository, key)

    monkeypatch.setattr(CrawlerSubmitter, "find_replay", hide_later_replay_once)

    response = _service(db_session).emit_catalogue(catalogue.id, api_key=api_key)

    assert (response.created_count, response.skipped_count, response.replayed_count) == (1, 0, 1)
    assert response.items[0].suggestion_id is not None
    replayed = next(item for item in response.items if item.claim_id == later.id)
    assert replayed.suggestion_id == replay.id
    assert _count(db_session, Suggestion) == 2


def test_emit_catalogue_reports_a_metadata_claim_as_skipped(db_session: Session) -> None:
    catalogue = _catalogue(db_session)
    entity = _entity(db_session, catalogue)
    _claim(db_session, entity, kind=DiscoveryClaimKind.METADATA, payload={})

    response = _service(db_session).emit_catalogue(catalogue.id, api_key=_api_key(db_session))

    assert response.items[0].skip_reason == SkipReason.METADATA_NOT_EMITTED
    assert response.skipped_count == 1


def test_emit_catalogue_reports_a_new_document_claim_without_a_url_as_skipped(db_session: Session) -> None:
    catalogue = _catalogue(db_session)
    entity = _entity(db_session, catalogue)
    _claim(db_session, entity, kind=DiscoveryClaimKind.NEW_DOCUMENT, payload={"title_i18n": {"de": "x"}})

    response = _service(db_session).emit_catalogue(catalogue.id, api_key=_api_key(db_session))

    assert response.items[0].skip_reason == SkipReason.INVALID_NEW_DOCUMENT_PAYLOAD


def test_emit_catalogue_reports_a_requirement_claim_without_documents_as_skipped(db_session: Session) -> None:
    catalogue = _catalogue(db_session)
    entity = _entity(db_session, catalogue)
    _claim(db_session, entity, kind=DiscoveryClaimKind.NEW_REQUIREMENT, payload={"notes_i18n": {"de": "x"}})

    response = _service(db_session).emit_catalogue(catalogue.id, api_key=_api_key(db_session))

    assert response.items[0].skip_reason == SkipReason.UNRESOLVED_REQUIREMENT_DOCUMENTS
    assert _count(db_session, Suggestion) == 0


def test_emit_catalogue_reports_a_claim_without_its_entity_as_skipped(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    catalogue = _catalogue(db_session)
    _new_document_claim(db_session, catalogue)
    repo = DiscoveryRepository(db_session)
    monkeypatch.setattr(repo, "list_catalogue_entities", lambda _id: [])
    taxonomy = TaxonomyService(TaxonomyRepository(db_session))
    documents = DocumentPromotion(DocumentRepository(db_session))
    events = EventLogService(EventLogRepository(db_session))
    suggestions = compose_suggestion_service(SuggestionRepository(db_session), documents, taxonomy, events)
    service = DiscoveryEmitService(repo, suggestions)

    response = service.emit_catalogue(catalogue.id, api_key=_api_key(db_session))

    assert response.items[0].skip_reason == SkipReason.MISSING_ENTITY
    assert _count(db_session, Suggestion) == 0


def test_emit_catalogue_replays_a_claim_emitted_before(db_session: Session) -> None:
    catalogue = _catalogue(db_session)
    _new_document_claim(db_session, catalogue)
    api_key = _api_key(db_session)
    service = _service(db_session)
    first = service.emit_catalogue(catalogue.id, api_key=api_key)

    second = service.emit_catalogue(catalogue.id, api_key=api_key)

    assert (first.created_count, first.replayed_count) == (1, 0)
    assert (second.created_count, second.replayed_count) == (0, 1)
    assert second.items[0].suggestion_id == first.items[0].suggestion_id
    assert _count(db_session, Suggestion) == 1


def test_emit_catalogue_records_the_emit_attempted_event_with_the_counts(db_session: Session) -> None:
    catalogue = _catalogue(db_session)
    _new_document_claim(db_session, catalogue)

    _service(db_session).emit_catalogue(catalogue.id, api_key=_api_key(db_session))

    events = list(db_session.scalars(select(DiscoveryEvent).where(DiscoveryEvent.catalogue_service_id == catalogue.id)))
    assert len(events) == 1
    assert events[0].payload["created_count"] == 1
    assert events[0].payload["claim_count"] == 1


def test_idempotency_keys_keep_their_stored_format(db_session: Session) -> None:
    catalogue = _catalogue(db_session)
    claim = _new_document_claim(db_session, catalogue)

    response = _service(db_session).emit_catalogue(catalogue.id, api_key=_api_key(db_session))

    suggestion = db_session.get(Suggestion, response.items[0].suggestion_id)
    assert suggestion is not None
    assert suggestion.idempotency_key == f"discovery-emit:{claim.id}"
    assert idempotency_key("emit", claim.id) == f"discovery-emit:{claim.id}"
    assert idempotency_key("candidate-emit", claim.id) == f"discovery-candidate-emit:{claim.id}"


# --- Red: a suggestion-rule failure skips one item instead of aborting the batch -------------


def test_emit_catalogue_skips_a_duplicate_claim_and_emits_the_rest(db_session: Session) -> None:
    catalogue = _catalogue(db_session)
    shared_entity = _entity(db_session, catalogue, url="https://example.gov/dup")
    first = _new_document_claim(db_session, catalogue, title="Same Title", entity=shared_entity)
    dup = _new_document_claim(db_session, catalogue, title="Same Title", entity=shared_entity)
    _new_document_claim(db_session, catalogue, url="https://example.gov/other", title="Other")

    response = _service(db_session).emit_catalogue(catalogue.id, api_key=_api_key(db_session))

    assert (response.created_count, response.skipped_count) == (2, 1)
    duplicate_items = [item for item in response.items if item.skip_reason == SkipReason.DUPLICATE]
    assert len(duplicate_items) == 1
    assert duplicate_items[0].claim_id in (first.id, dup.id)
    assert duplicate_items[0].suggestion_id is None
    assert _count(db_session, Suggestion) == 2


def test_emit_catalogue_skips_a_claim_with_an_unknown_category_code(db_session: Session) -> None:
    catalogue = _catalogue(db_session)
    _new_document_claim(db_session, catalogue, category_codes=["no-such-category"])

    response = _service(db_session).emit_catalogue(catalogue.id, api_key=_api_key(db_session))

    assert response.items[0].skip_reason == SkipReason.INVALID_PAYLOAD
    assert _count(db_session, Suggestion) == 0


def test_emit_catalogue_skips_a_claim_whose_body_does_not_validate(db_session: Session) -> None:
    catalogue = _catalogue(db_session)
    entity = _entity(db_session, catalogue, url="https://example.gov/doc")
    _claim(
        db_session,
        entity,
        kind=DiscoveryClaimKind.NEW_DOCUMENT,
        payload={"title_i18n": {"de": "x"}, "official_url": "ftp://example.gov/x"},
    )

    response = _service(db_session).emit_catalogue(catalogue.id, api_key=_api_key(db_session))

    assert response.items[0].skip_reason == SkipReason.INVALID_PAYLOAD
    assert _count(db_session, Suggestion) == 0


def test_emit_catalogue_skips_a_requirement_claim_pointing_outside_the_jurisdiction(db_session: Session) -> None:
    catalogue = _catalogue(db_session)
    other = Jurisdiction(kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Otherland"}, code=f"O{uuid.uuid4().hex[:6]}")
    db_session.add(other)
    db_session.flush()
    parent = Document(jurisdiction_id=catalogue.jurisdiction_id, slug="parent-doc", title_i18n={"en": "Parent"})
    required = Document(jurisdiction_id=other.id, slug="required-doc", title_i18n={"en": "Required"})
    db_session.add_all([parent, required])
    db_session.flush()
    _requirement_claim(db_session, catalogue, parent_id=parent.id, required_id=required.id)

    response = _service(db_session).emit_catalogue(catalogue.id, api_key=_api_key(db_session))

    assert response.items[0].skip_reason == SkipReason.INVALID_PAYLOAD
    assert _count(db_session, Suggestion) == 0


def test_skip_reason_values_are_the_ten_wire_strings() -> None:
    assert {member.value for member in SkipReason} == {
        "not_found",
        "no_mentions",
        "no_source_url",
        "invalid_payload",
        "duplicate",
        "already_emitted",
        "missing_entity",
        "metadata_not_emitted",
        "invalid_new_document_payload",
        "unresolved_requirement_documents",
    }


class _StubSuggestions:
    def __init__(self, to_raise: Exception | None) -> None:
        self._to_raise = to_raise

    def create(self, *, submitter: object, request: object, idempotency_key: str) -> object:
        if self._to_raise is not None:
            raise self._to_raise
        return "submitted"


@pytest.mark.parametrize(
    "exc,expected_reason",
    [
        (DuplicateSuggestionError([]), SkipReason.DUPLICATE),
        (UnknownTaxonomyCodeError("bad code"), SkipReason.INVALID_PAYLOAD),
        (UnknownDocumentError("outside jurisdiction"), SkipReason.INVALID_PAYLOAD),
        (CycleError("would cycle"), SkipReason.INVALID_PAYLOAD),
        (MissingSourceUrlError("missing"), SkipReason.NO_SOURCE_URL),
    ],
)
def test_submit_or_skip_maps_each_suggestion_rule_error(exc: Exception, expected_reason: SkipReason) -> None:
    stub = _StubSuggestions(exc)

    with pytest.raises(EmitSkip) as excinfo:
        submit_or_skip(
            stub,  # type: ignore[arg-type]
            submitter=CrawlerSubmitter(uuid.uuid4()),
            request=object(),  # type: ignore[arg-type]
            idempotency_key="k",
        )

    assert excinfo.value.reason == expected_reason
    if isinstance(exc, DuplicateSuggestionError):
        assert excinfo.value.conflicts == exc.conflicts


def test_submit_or_skip_lets_unknown_jurisdiction_propagate() -> None:
    stub = _StubSuggestions(UnknownJurisdictionError("no such jurisdiction"))

    with pytest.raises(UnknownJurisdictionError):
        submit_or_skip(
            stub,  # type: ignore[arg-type]
            submitter=CrawlerSubmitter(uuid.uuid4()),
            request=object(),  # type: ignore[arg-type]
            idempotency_key="k",
        )


def test_submit_or_skip_lets_an_unexpected_value_error_propagate() -> None:
    stub = _StubSuggestions(ValueError("not one of ours"))

    with pytest.raises(ValueError, match="not one of ours"):
        submit_or_skip(
            stub,  # type: ignore[arg-type]
            submitter=CrawlerSubmitter(uuid.uuid4()),
            request=object(),  # type: ignore[arg-type]
            idempotency_key="k",
        )


def test_submit_or_skip_returns_the_submission_result_on_success() -> None:
    stub = _StubSuggestions(None)

    result = submit_or_skip(
        stub,  # type: ignore[arg-type]
        submitter=CrawlerSubmitter(uuid.uuid4()),
        request=object(),  # type: ignore[arg-type]
        idempotency_key="k",
    )

    assert result == "submitted"


def test_suggestion_rule_reasons_table_covers_the_four_mapped_errors() -> None:
    assert {
        UnknownTaxonomyCodeError: SkipReason.INVALID_PAYLOAD,
        UnknownDocumentError: SkipReason.INVALID_PAYLOAD,
        CycleError: SkipReason.INVALID_PAYLOAD,
        MissingSourceUrlError: SkipReason.NO_SOURCE_URL,
    } == SUGGESTION_RULE_REASONS
