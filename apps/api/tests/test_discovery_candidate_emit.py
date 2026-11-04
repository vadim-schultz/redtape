"""Emit a staged document candidate as a pending ``new_document`` suggestion (chapter 11, loop B)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.features.discovery.candidate_emit import DiscoveryCandidateEmitService
from app.features.discovery.candidate_emit_payload import SuggestedTags
from app.features.discovery.repository import DiscoveryRepository
from app.features.documents.promotion import DocumentPromotion
from app.features.documents.repository import DocumentRepository
from app.features.events.repository import EventLogRepository
from app.features.events.service import EventLogService
from app.features.suggestions.repository import SuggestionRepository
from app.features.taxonomy.repository import TaxonomyRepository
from app.features.taxonomy.service import TaxonomyService
from app.models.api_key import ApiKey
from app.models.discovery import (
    CatalogueService,
    DiscoveryCandidateMention,
    DiscoveryCandidateStatus,
    DiscoveryDocumentCandidate,
    DiscoveryMentionRole,
)
from app.models.document import Document
from app.models.suggestion import Suggestion, SuggestionSource, SuggestionStatus
from litestar import Litestar
from litestar.testing import TestClient
from scripts.seed_taxonomy import seed_taxonomy
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from suggestion_support import compose_suggestion_service
from test_discovery_admin_api import ADMIN_EMAIL, _catalogue, _token
from test_discovery_admin_api import client as client  # noqa: F401
from test_discovery_machine_api import _issue_key

EMIT_URL = "/api/v1/discovery/machine/candidates/emit"
PREVIEW_URL = "/api/v1/discovery/admin/candidates/{id}/emit-preview"
PROCEDURE_URL = "https://example.gov/service"
NOW = datetime(2026, 10, 26, tzinfo=UTC)


def _bearer(email: str = ADMIN_EMAIL) -> dict[str, str]:
    sub = uuid.uuid5(uuid.NAMESPACE_URL, email)
    return {"Authorization": f"Bearer {_token(sub=sub, email=email)}"}


def _candidate(
    db_session: Session, catalogue: CatalogueService, *, key: str = "personalausweis", **fields: object
) -> DiscoveryDocumentCandidate:
    row = DiscoveryDocumentCandidate(
        jurisdiction_id=catalogue.jurisdiction_id, key=key, title_i18n={"de": key.title()}, **fields
    )
    db_session.add(row)
    db_session.flush()
    return row


def _mention(
    db_session: Session, candidate: DiscoveryDocumentCandidate, catalogue: CatalogueService, *, age_days: int = 0
) -> None:
    db_session.add(
        DiscoveryCandidateMention(
            candidate_id=candidate.id,
            catalogue_service_id=catalogue.id,
            role=DiscoveryMentionRole.REQUIRED,
            excerpt="Bitte mitbringen",
            source_field=f"details[{age_days}]",
            extractor="pvog-payload",
            extractor_version="1",
            created_at=NOW - timedelta(days=age_days),
        )
    )
    db_session.flush()


def _staged(
    db_session: Session, *, portal_url: str | None = PROCEDURE_URL, **fields: object
) -> tuple[DiscoveryDocumentCandidate, CatalogueService]:
    catalogue = _catalogue(db_session, external_id=uuid.uuid4().hex)
    catalogue.portal_url = portal_url
    candidate = _candidate(db_session, catalogue, **fields)
    _mention(db_session, candidate, catalogue)
    return candidate, catalogue


def _emit(client: TestClient[Litestar], key: str, *candidate_ids: uuid.UUID):  # noqa: F811
    body = {"candidate_ids": [str(i) for i in candidate_ids]}
    return client.post(EMIT_URL, json=body, headers={"X-API-Key": key})


def _count(db_session: Session, model: type) -> int:
    return int(db_session.scalar(select(func.count()).select_from(model)) or 0)


def test_emit_creates_a_pending_suggestion_and_marks_the_candidate_emitted(
    client: TestClient[Litestar],
    db_session: Session,  # noqa: F811
) -> None:
    candidate, catalogue = _staged(db_session, official_url="https://example.gov/ausweis")
    later = _catalogue(db_session, external_id="svc-later")
    later.portal_url = "https://example.gov/later"
    _mention(db_session, candidate, later, age_days=-5)

    response = _emit(client, _issue_key(db_session), candidate.id)

    body = response.json()
    assert response.status_code == 200
    assert (body["created_count"], body["replayed_count"], body["skipped_count"]) == (1, 0, 0)
    [item] = body["items"]
    suggestion = db_session.get(Suggestion, uuid.UUID(item["suggestion_id"]))
    assert suggestion is not None
    assert (suggestion.status, suggestion.source_type) == (SuggestionStatus.PENDING, SuggestionSource.CRAWLER)
    assert suggestion.source_url == PROCEDURE_URL
    assert suggestion.payload["title_i18n"] == {"de": "Personalausweis"}
    assert suggestion.payload["official_url"] == "https://example.gov/ausweis"
    assert (candidate.status, candidate.suggestion_id) == (DiscoveryCandidateStatus.EMITTED, suggestion.id)


def test_emit_of_a_url_less_candidate_creates_a_url_less_suggestion(
    client: TestClient[Litestar],
    db_session: Session,  # noqa: F811
) -> None:
    candidate, _ = _staged(db_session)

    response = _emit(client, _issue_key(db_session), candidate.id)

    [item] = response.json()["items"]
    suggestion = db_session.get(Suggestion, uuid.UUID(item["suggestion_id"]))
    assert suggestion is not None
    assert (suggestion.payload["official_url"], suggestion.normalized_url) == (None, None)


def test_emit_replay_is_idempotent(client: TestClient[Litestar], db_session: Session) -> None:  # noqa: F811
    candidate, _ = _staged(db_session)
    key = _issue_key(db_session)
    first = _emit(client, key, candidate.id).json()["items"][0]

    again = _emit(client, key, candidate.id).json()
    candidate.status, candidate.suggestion_id = DiscoveryCandidateStatus.STAGED, None
    db_session.flush()
    after_reset = _emit(client, key, candidate.id).json()

    for body in (again, after_reset):
        assert body["items"][0]["suggestion_id"] == first["suggestion_id"]
        assert (body["created_count"], body["replayed_count"]) == (0, 1)
    assert _count(db_session, Suggestion) == 1
    assert candidate.status == DiscoveryCandidateStatus.EMITTED


def test_emit_reports_a_slug_conflict_as_a_skipped_candidate(
    client: TestClient[Litestar],
    db_session: Session,  # noqa: F811
) -> None:
    candidate, catalogue = _staged(db_session)
    document = Document(
        jurisdiction_id=catalogue.jurisdiction_id, slug="personalausweis", title_i18n={"de": "Personalausweis"}
    )
    db_session.add(document)
    db_session.flush()

    body = _emit(client, _issue_key(db_session), candidate.id).json()

    [item] = body["items"]
    assert (item["skip_reason"], item["suggestion_id"]) == ("duplicate", None)
    assert item["conflicts"] == [{"type": "document", "id": str(document.id)}]
    assert (body["created_count"], body["skipped_count"]) == (0, 1)
    assert (candidate.status, candidate.suggestion_id) == (DiscoveryCandidateStatus.STAGED, None)
    assert _count(db_session, Suggestion) == 0


def test_emit_skips_candidates_that_cannot_form_a_valid_suggestion(
    client: TestClient[Litestar],
    db_session: Session,  # noqa: F811
) -> None:
    unmentioned = _candidate(db_session, _catalogue(db_session, external_id="svc-x"), key="reisepass")
    no_page, _ = _staged(db_session, portal_url=None, key="geburtsurkunde")
    broken, _ = _staged(db_session, key="meldebescheinigung", official_url="ftp://example.gov/form")

    items = _emit(client, _issue_key(db_session), unmentioned.id, no_page.id, broken.id).json()["items"]

    reasons = {item["candidate_id"]: item["skip_reason"] for item in items}
    assert reasons[str(unmentioned.id)] == "no_mentions"
    assert reasons[str(no_page.id)] == "no_source_url"
    assert reasons[str(broken.id)] == "invalid_payload"
    assert _count(db_session, Suggestion) == 0


def test_emit_of_an_unknown_candidate_is_reported_per_item(
    client: TestClient[Litestar],
    db_session: Session,  # noqa: F811
) -> None:
    candidate, _ = _staged(db_session)
    unknown = uuid.uuid4()

    body = _emit(client, _issue_key(db_session), unknown, candidate.id).json()

    by_id = {item["candidate_id"]: item for item in body["items"]}
    assert by_id[str(unknown)]["skip_reason"] == "not_found"
    assert by_id[str(candidate.id)]["skip_reason"] is None
    assert (body["created_count"], body["skipped_count"]) == (1, 1)


def test_emit_rejects_an_empty_or_oversized_batch(client: TestClient[Litestar], db_session: Session) -> None:  # noqa: F811
    key = _issue_key(db_session)

    assert _emit(client, key).status_code == 422
    assert _emit(client, key, *[uuid.uuid4() for _ in range(51)]).status_code == 422


def test_emit_preview_never_writes(client: TestClient[Litestar], db_session: Session) -> None:  # noqa: F811
    candidate, catalogue = _staged(db_session, official_url="https://example.gov/ausweis")

    response = client.get(PREVIEW_URL.format(id=candidate.id), headers=_bearer())

    body = response.json()
    assert response.status_code == 200
    assert body["skip_reason"] is None
    assert body["suggestion"]["kind"] == "new_document"
    assert body["suggestion"]["jurisdiction_id"] == str(catalogue.jurisdiction_id)
    assert body["suggestion"]["source_url"] == PROCEDURE_URL
    assert body["suggestion"]["payload"]["official_url"] == "https://example.gov/ausweis"
    assert _count(db_session, Suggestion) == 0
    assert (candidate.status, candidate.suggestion_id) == (DiscoveryCandidateStatus.STAGED, None)


def test_emit_preview_reports_why_a_candidate_would_be_skipped(
    client: TestClient[Litestar],
    db_session: Session,  # noqa: F811
) -> None:
    candidate, catalogue = _staged(db_session)
    db_session.add(Document(jurisdiction_id=catalogue.jurisdiction_id, slug="personalausweis", title_i18n={"de": "x"}))
    db_session.flush()

    body = client.get(PREVIEW_URL.format(id=candidate.id), headers=_bearer()).json()

    assert (body["skip_reason"], body["suggestion"]) == ("duplicate", None)
    assert [c["type"] for c in body["conflicts"]] == ["document"]
    assert _count(db_session, Suggestion) == 0


def test_emit_preview_of_an_emitted_candidate_reports_already_emitted(
    client: TestClient[Litestar],
    db_session: Session,  # noqa: F811
) -> None:
    candidate, _ = _staged(db_session)
    key = _issue_key(db_session)
    _emit(client, key, candidate.id)

    response = client.get(PREVIEW_URL.format(id=candidate.id), headers=_bearer())

    body = response.json()
    assert response.status_code == 200
    assert body["skip_reason"] == "already_emitted"
    assert body["suggestion"] is None


def test_emit_preview_of_an_unknown_candidate_is_404(client: TestClient[Litestar]) -> None:  # noqa: F811
    response = client.get(PREVIEW_URL.format(id=uuid.uuid4()), headers=_bearer())

    assert response.status_code == 404


def test_emit_requires_the_machine_key_and_preview_requires_an_admin(
    client: TestClient[Litestar],
    db_session: Session,  # noqa: F811
) -> None:
    candidate, _ = _staged(db_session)
    preview = PREVIEW_URL.format(id=candidate.id)
    body = {"candidate_ids": [str(candidate.id)]}

    assert client.post(EMIT_URL, json=body).status_code == 401
    assert client.post(EMIT_URL, json=body, headers=_bearer()).status_code == 403
    assert client.get(preview).status_code == 401
    assert client.get(preview, headers=_bearer("stranger@example.com")).status_code == 403
    assert _count(db_session, Suggestion) == 0


def test_machine_preview_and_listing_let_the_worker_select_without_writing(
    client: TestClient[Litestar],
    db_session: Session,  # noqa: F811
) -> None:
    busy, catalogue = _staged(db_session)
    _mention(db_session, busy, catalogue, age_days=1)
    quiet = _candidate(db_session, catalogue, key="reisepass")
    _mention(db_session, quiet, catalogue)
    headers = {"X-API-Key": _issue_key(db_session)}
    listing_url = "/api/v1/discovery/machine/candidates"

    listing = client.get(listing_url, params={"status": "staged", "min_mentions": 2, "limit": 5}, headers=headers)
    preview = client.get(f"{listing_url}/{busy.id}/emit-preview", headers=headers)

    assert [item["id"] for item in listing.json()["items"]] == [str(busy.id)]
    assert preview.json()["suggestion"]["payload"]["title_i18n"] == {"de": "Personalausweis"}
    assert client.get(listing_url).status_code == 401
    assert _count(db_session, Suggestion) == 0


@pytest.fixture
def api_key(db_session: Session) -> ApiKey:
    row = ApiKey(name="crawler", key_hash=uuid.uuid4().hex, key_prefix=uuid.uuid4().hex[:8])
    db_session.add(row)
    db_session.flush()
    return row


def _tagged_service(db_session: Session, tags: SuggestedTags) -> DiscoveryCandidateEmitService:
    taxonomy = TaxonomyService(TaxonomyRepository(db_session))
    documents = DocumentPromotion(DocumentRepository(db_session), taxonomy)
    events = EventLogService(EventLogRepository(db_session))
    suggestions = compose_suggestion_service(SuggestionRepository(db_session), documents, taxonomy, events)
    return DiscoveryCandidateEmitService(
        DiscoveryRepository(db_session), suggestions, lambda _session, _candidate: tags
    )


def test_payload_carries_the_codes_the_tag_hook_returns_and_the_preview_prints_them(
    db_session: Session, api_key: ApiKey
) -> None:
    seed_taxonomy(db_session)
    candidate, _ = _staged(db_session)
    service = _tagged_service(db_session, SuggestedTags(["housing"], ["moving-house"]))

    preview = service.preview(candidate.id)
    result = service.emit(candidate.id, api_key)

    assert preview.suggestion is not None
    assert preview.suggestion.payload.model_dump()["category_codes"] == ["home-and-housing", "moving-house"]
    suggestion = db_session.get(Suggestion, result.suggestion_id)
    assert suggestion is not None
    assert suggestion.payload["category_codes"] == ["home-and-housing", "moving-house"]


def test_payload_has_no_codes_when_the_tag_hook_returns_none(db_session: Session, api_key: ApiKey) -> None:
    candidate, _ = _staged(db_session)
    service = _tagged_service(db_session, SuggestedTags([], []))

    result = service.emit(candidate.id, api_key)

    suggestion = db_session.get(Suggestion, result.suggestion_id)
    assert suggestion is not None
    assert suggestion.payload.get("category_codes", []) == []


def test_an_unknown_code_from_the_tag_hook_skips_the_candidate_as_invalid(db_session: Session, api_key: ApiKey) -> None:
    candidate, _ = _staged(db_session)
    service = _tagged_service(db_session, SuggestedTags(["no-such-domain"], []))

    result = service.emit(candidate.id, api_key)

    assert result.skip_reason == "invalid_payload"
    assert candidate.status == DiscoveryCandidateStatus.STAGED
    assert _count(db_session, Suggestion) == 0


def _tagged_mention(
    db_session: Session,
    candidate: DiscoveryDocumentCandidate,
    domains: list[str],
    situations: list[str],
    *,
    external_id: str,
) -> None:
    catalogue = _catalogue(db_session, external_id=external_id)
    catalogue.portal_url = PROCEDURE_URL
    _mention(db_session, candidate, catalogue)
    row = db_session.scalars(
        select(DiscoveryCandidateMention).where(DiscoveryCandidateMention.catalogue_service_id == catalogue.id)
    ).one()
    row.domain_codes, row.situation_codes = domains, situations
    db_session.flush()
    db_session.expire(candidate)


def _default_service(db_session: Session) -> DiscoveryCandidateEmitService:
    taxonomy = TaxonomyService(TaxonomyRepository(db_session))
    documents = DocumentPromotion(DocumentRepository(db_session), taxonomy)
    events = EventLogService(EventLogRepository(db_session))
    suggestions = compose_suggestion_service(SuggestionRepository(db_session), documents, taxonomy, events)
    return DiscoveryCandidateEmitService(DiscoveryRepository(db_session), suggestions)


def test_emit_payload_carries_the_domain_codes_the_mentions_agree_on(db_session: Session, api_key: ApiKey) -> None:
    seed_taxonomy(db_session)
    candidate, _ = _staged(db_session)
    _tagged_mention(db_session, candidate, ["housing"], ["moving-house"], external_id="svc-a")
    _tagged_mention(db_session, candidate, ["housing"], ["birth-of-child"], external_id="svc-b")

    result = _default_service(db_session).emit(candidate.id, api_key)

    suggestion = db_session.get(Suggestion, result.suggestion_id)
    assert suggestion is not None
    assert suggestion.payload["category_codes"] == [
        "home-and-housing",
        "birth-and-parenthood",
        "moving-house",
    ]


def test_emit_payload_includes_a_single_procedure_code_on_either_axis(db_session: Session, api_key: ApiKey) -> None:
    """situation-tag-hierarchy chapter 1: the binary accept/reject gate is gone, so a single procedure's
    code clears the small inclusion floor on either axis now — not just situation's old relaxed rule.
    """
    seed_taxonomy(db_session)
    candidate, _ = _staged(db_session)
    _tagged_mention(db_session, candidate, ["housing"], ["moving-house"], external_id="svc-a")

    result = _default_service(db_session).emit(candidate.id, api_key)

    suggestion = db_session.get(Suggestion, result.suggestion_id)
    assert suggestion is not None
    assert suggestion.payload["category_codes"] == ["home-and-housing", "moving-house"]
