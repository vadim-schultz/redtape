"""Admin read routes for document candidates (chapter 6, loop D)."""

from __future__ import annotations

import uuid

from app.models.discovery import (
    CatalogueService,
    DiscoveryCandidateMention,
    DiscoveryCandidateStatus,
    DiscoveryDocumentCandidate,
    DiscoveryMentionRole,
)
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy.orm import Session

from test_discovery_admin_api import ADMIN_EMAIL, _catalogue, _token

CANDIDATES_URL = "/api/v1/discovery/admin/candidates"


def _auth(email: str = ADMIN_EMAIL) -> dict[str, str]:
    sub = uuid.uuid5(uuid.NAMESPACE_URL, email)
    return {"Authorization": f"Bearer {_token(sub=sub, email=email)}"}


def _candidate(
    db_session: Session,
    catalogue: CatalogueService,
    *,
    key: str,
    status: DiscoveryCandidateStatus = DiscoveryCandidateStatus.STAGED,
) -> DiscoveryDocumentCandidate:
    row = DiscoveryDocumentCandidate(
        jurisdiction_id=catalogue.jurisdiction_id, key=key, title_i18n={"de": key.title()}, status=status
    )
    db_session.add(row)
    db_session.flush()
    return row


def _mention(
    db_session: Session, candidate: DiscoveryDocumentCandidate, catalogue: CatalogueService, field: str = "details[0]"
) -> DiscoveryCandidateMention:
    row = DiscoveryCandidateMention(
        candidate_id=candidate.id,
        catalogue_service_id=catalogue.id,
        role=DiscoveryMentionRole.REQUIRED,
        excerpt="Bitte mitbringen",
        source_field=field,
        extractor="pvog_payload",
        extractor_version="1",
    )
    db_session.add(row)
    db_session.flush()
    return row


def test_admin_candidate_list_returns_mention_counts_and_filters_by_status(
    client: TestClient[Litestar], db_session: Session
) -> None:
    catalogue = _catalogue(db_session)
    busy = _candidate(db_session, catalogue, key="personalausweis")
    _candidate(db_session, catalogue, key="reisepass", status=DiscoveryCandidateStatus.EMITTED)
    _mention(db_session, busy, catalogue, "a")
    _mention(db_session, busy, catalogue, "b")

    everything = client.get(CANDIDATES_URL, headers=_auth()).json()
    staged = client.get(CANDIDATES_URL, params={"status": "staged"}, headers=_auth()).json()

    assert everything["total"] == 2
    counts = {item["key"]: item["mention_count"] for item in everything["items"]}
    assert counts == {"personalausweis": 2, "reisepass": 0}
    assert [item["key"] for item in staged["items"]] == ["personalausweis"]
    assert staged["total"] == 1


def test_admin_candidate_list_pages_with_offset_and_limit(client: TestClient[Litestar], db_session: Session) -> None:
    catalogue = _catalogue(db_session)
    for key in ("a-doc", "b-doc", "c-doc"):
        _candidate(db_session, catalogue, key=key)

    body = client.get(CANDIDATES_URL, params={"offset": 1, "limit": 1}, headers=_auth()).json()

    assert (body["total"], body["offset"], body["limit"], len(body["items"])) == (3, 1, 1, 1)


def test_admin_candidate_detail_returns_mentions_with_procedure_titles(
    client: TestClient[Litestar], db_session: Session
) -> None:
    catalogue = _catalogue(db_session)
    catalogue.portal_url = "https://example.gov/service"
    candidate = _candidate(db_session, catalogue, key="personalausweis")
    mention = _mention(db_session, candidate, catalogue)

    body = client.get(f"{CANDIDATES_URL}/{candidate.id}", headers=_auth()).json()

    assert body["candidate"]["id"] == str(candidate.id)
    assert body["candidate"]["mention_count"] == 1
    [row] = body["mentions"]
    assert row["id"] == str(mention.id)
    assert row["role"] == "required"
    assert row["procedure_title_i18n"] == {"de": "Leistung"}
    assert row["procedure_source"] == "govdata"
    assert row["portal_url"] == "https://example.gov/service"


def test_admin_candidate_routes_reject_non_admins(client: TestClient[Litestar], db_session: Session) -> None:
    candidate = _candidate(db_session, _catalogue(db_session), key="personalausweis")

    listing = client.get(CANDIDATES_URL, headers=_auth("stranger@example.com"))
    detail = client.get(f"{CANDIDATES_URL}/{candidate.id}", headers=_auth("stranger@example.com"))

    assert (listing.status_code, detail.status_code) == (403, 403)


def test_admin_candidate_routes_reject_anonymous_requests(client: TestClient[Litestar]) -> None:
    assert client.get(CANDIDATES_URL).status_code == 401


def test_unknown_candidate_is_404(client: TestClient[Litestar]) -> None:
    response = client.get(f"{CANDIDATES_URL}/{uuid.uuid4()}", headers=_auth())

    assert response.status_code == 404
    assert response.json()["detail"] == "Document candidate not found"
