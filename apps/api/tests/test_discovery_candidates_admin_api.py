"""Admin read routes for document candidates (chapter 6, loop D)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.models.discovery import (
    CatalogueService,
    DiscoveryArtifact,
    DiscoveryArtifactKind,
    DiscoveryCandidateMention,
    DiscoveryCandidateStatus,
    DiscoveryDocumentCandidate,
    DiscoveryMentionRole,
    DiscoverySource,
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
    title_i18n: dict[str, str] | None = None,
) -> DiscoveryDocumentCandidate:
    row = DiscoveryDocumentCandidate(
        jurisdiction_id=catalogue.jurisdiction_id,
        key=key,
        title_i18n=title_i18n or {"de": key.title()},
        status=status,
    )
    db_session.add(row)
    db_session.flush()
    return row


def _mention(
    db_session: Session,
    candidate: DiscoveryDocumentCandidate,
    catalogue: CatalogueService,
    field: str = "details[0]",
    role: DiscoveryMentionRole = DiscoveryMentionRole.REQUIRED,
    artifact: DiscoveryArtifact | None = None,
) -> DiscoveryCandidateMention:
    row = DiscoveryCandidateMention(
        candidate_id=candidate.id,
        artifact_id=artifact.id if artifact else None,
        catalogue_service_id=catalogue.id,
        role=role,
        excerpt="Bitte mitbringen",
        source_field=field,
        extractor="pvog_payload",
        extractor_version="1",
    )
    db_session.add(row)
    db_session.flush()
    return row


def _artifact(
    db_session: Session,
    catalogue: CatalogueService,
    kind: DiscoveryArtifactKind = DiscoveryArtifactKind.HTML_SNAPSHOT,
    *,
    fetched_at: datetime | None = None,
) -> DiscoveryArtifact:
    sha = uuid.uuid4().hex + uuid.uuid4().hex
    row = DiscoveryArtifact(
        catalogue_service_id=catalogue.id,
        kind=kind,
        storage_key=f"discovery/{catalogue.id}/{kind.value}/{sha}",
        sha256=sha,
        content_type="text/html" if kind is DiscoveryArtifactKind.HTML_SNAPSHOT else "image/png",
        byte_size=10,
        source_url="https://example.gov/page",
        fetched_at=fetched_at or datetime(2026, 10, 26, 12, 0, tzinfo=UTC),
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


def test_admin_candidate_detail_shows_mention_conditions_codes_and_suggested_tags(
    client: TestClient[Litestar], db_session: Session
) -> None:
    first = _catalogue(db_session, external_id="svc-a")
    second = _catalogue(db_session, external_id="svc-b")
    candidate = _candidate(db_session, first, key="personalausweis")
    for catalogue, situations in ((first, ["moving-house"]), (second, ["moving-house", "birth-of-child"])):
        row = _mention(db_session, candidate, catalogue)
        row.condition, row.is_optional = "bei Zuzug", False
        row.domain_codes, row.situation_codes = ["housing"], situations
    db_session.flush()

    body = client.get(f"{CANDIDATES_URL}/{candidate.id}", headers=_auth()).json()

    mention = next(m for m in body["mentions"] if m["catalogue_service_id"] == str(first.id))
    assert (mention["condition"], mention["is_optional"]) == ("bei Zuzug", False)
    assert (mention["domain_codes"], mention["situation_codes"]) == (["housing"], ["moving-house"])
    assert body["suggested_domain_codes"] == [{"code": "housing", "procedures": 2, "share": 1.0, "accepted": True}]
    assert body["suggested_situation_codes"] == [
        {"code": "moving-house", "procedures": 2, "share": 1.0, "accepted": True},
        {"code": "birth-of-child", "procedures": 1, "share": 0.5, "accepted": False},
    ]


def test_admin_candidate_detail_has_empty_suggestions_and_codes_without_tagged_mentions(
    client: TestClient[Litestar], db_session: Session
) -> None:
    catalogue = _catalogue(db_session)
    candidate = _candidate(db_session, catalogue, key="personalausweis")
    _mention(db_session, candidate, catalogue)

    body = client.get(f"{CANDIDATES_URL}/{candidate.id}", headers=_auth()).json()

    assert (body["suggested_domain_codes"], body["suggested_situation_codes"]) == ([], [])
    assert body["mentions"][0]["domain_codes"] == []
    assert (body["mentions"][0]["condition"], body["mentions"][0]["is_optional"]) == (None, None)


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


def _keys(client: TestClient[Litestar], **params: object) -> list[str]:
    body = client.get(CANDIDATES_URL, params=params, headers=_auth()).json()
    return [item["key"] for item in body["items"]]


def test_candidate_list_filters_by_q_across_locales(client: TestClient[Litestar], db_session: Session) -> None:
    catalogue = _catalogue(db_session)
    _candidate(db_session, catalogue, key="personalausweis", title_i18n={"de": "Personalausweis"})
    _candidate(
        db_session, catalogue, key="birth-certificate", title_i18n={"de": "Geburtsurkunde", "en": "Birth certificate"}
    )
    _candidate(db_session, catalogue, key="passport", title_i18n={"en": "Passport"})

    assert _keys(client, q="PERSONAL") == ["personalausweis"]
    assert _keys(client, q="certificate") == ["birth-certificate"]
    assert _keys(client, q="pass") == ["passport"]


def test_candidate_list_q_matches_titles_literally_and_total_follows(
    client: TestClient[Litestar], db_session: Session
) -> None:
    catalogue = _catalogue(db_session)
    _candidate(db_session, catalogue, key="personalausweis", title_i18n={"de": "Personalausweis"})
    _candidate(db_session, catalogue, key="reisepass", title_i18n={"de": "Pass"})

    nothing = client.get(CANDIDATES_URL, params={"q": "%"}, headers=_auth()).json()
    some = client.get(CANDIDATES_URL, params={"q": "ausweis"}, headers=_auth()).json()
    by_key = _keys(client, q="reisepass")

    assert (nothing["items"], nothing["total"]) == ([], 0)
    assert some["total"] == 1
    assert by_key == []


def test_candidate_list_filters_by_min_mentions_role_and_source(
    client: TestClient[Litestar], db_session: Session
) -> None:
    govdata = _catalogue(db_session)
    pvog = _catalogue(db_session, source=DiscoverySource.PVOG, external_id="svc-2")
    busy = _candidate(db_session, govdata, key="busy")
    form = _candidate(db_session, govdata, key="form-only")
    _candidate(db_session, govdata, key="unmentioned")
    _mention(db_session, busy, govdata, "a")
    _mention(db_session, busy, pvog, "b")
    _mention(db_session, form, pvog, "c", DiscoveryMentionRole.FORM)

    assert sorted(_keys(client, min_mentions=1)) == ["busy", "form-only"]
    assert _keys(client, min_mentions=2) == ["busy"]
    assert _keys(client, role="form") == ["form-only"]
    assert _keys(client, role="required") == ["busy"]
    assert sorted(_keys(client, source="pvog")) == ["busy", "form-only"]
    assert _keys(client, source="govdata") == ["busy"]
    assert _keys(client, source="pvog", role="form", min_mentions=1) == ["form-only"]


def test_candidate_list_filters_keep_total_and_counts_consistent(
    client: TestClient[Litestar], db_session: Session
) -> None:
    govdata = _catalogue(db_session)
    pvog = _catalogue(db_session, source=DiscoverySource.PVOG, external_id="svc-2")
    busy = _candidate(db_session, govdata, key="busy")
    _mention(db_session, busy, govdata, "a")
    _mention(db_session, busy, pvog, "b", DiscoveryMentionRole.FORM)

    body = client.get(CANDIDATES_URL, params={"source": "pvog", "min_mentions": 3}, headers=_auth()).json()
    kept = client.get(CANDIDATES_URL, params={"source": "pvog", "min_mentions": 2}, headers=_auth()).json()

    assert (body["items"], body["total"]) == ([], 0)
    [item] = kept["items"]
    assert (kept["total"], item["mention_count"], item["roles"]) == (1, 2, ["form", "required"])
    assert item["jurisdiction_name_i18n"] == {"en": "Testland"}


def test_candidate_list_sorts_by_mention_count_then_title(client: TestClient[Litestar], db_session: Session) -> None:
    catalogue = _catalogue(db_session)
    zebra = _candidate(db_session, catalogue, key="zebra", title_i18n={"de": "Zebra"})
    apple = _candidate(db_session, catalogue, key="apple", title_i18n={"de": "apfel"})
    popular = _candidate(db_session, catalogue, key="popular", title_i18n={"de": "Beliebt"})
    _mention(db_session, popular, catalogue, "a")
    _mention(db_session, popular, catalogue, "b")
    _mention(db_session, zebra, catalogue, "c")
    _mention(db_session, apple, catalogue, "d")

    assert _keys(client) == ["popular", "apple", "zebra"]
    assert _keys(client, sort="mentions_desc") == ["popular", "apple", "zebra"]
    assert _keys(client, sort="title_asc") == ["apple", "popular", "zebra"]


def test_candidate_list_sorts_newest_first_and_falls_back_to_english_titles(
    client: TestClient[Litestar], db_session: Session
) -> None:
    catalogue = _catalogue(db_session)
    older = _candidate(db_session, catalogue, key="older", title_i18n={"en": "Alpha"})
    newer = _candidate(db_session, catalogue, key="newer", title_i18n={"de": "Zeta"})
    older.created_at = newer.created_at - timedelta(days=1)
    db_session.flush()

    assert _keys(client, sort="newest") == ["newer", "older"]
    assert _keys(client, sort="title_asc") == ["older", "newer"]


def test_candidate_list_rejects_an_unknown_sort_or_role(client: TestClient[Litestar], db_session: Session) -> None:
    _candidate(db_session, _catalogue(db_session), key="personalausweis")

    bad_sort = client.get(CANDIDATES_URL, params={"sort": "random"}, headers=_auth())
    bad_role = client.get(CANDIDATES_URL, params={"role": "optional"}, headers=_auth())
    bad_source = client.get(CANDIDATES_URL, params={"source": "nowhere"}, headers=_auth())
    bad_minimum = client.get(CANDIDATES_URL, params={"min_mentions": -1}, headers=_auth())

    assert [r.status_code for r in (bad_sort, bad_role, bad_source, bad_minimum)] == [422, 422, 422, 422]


def test_admin_candidate_detail_includes_an_artifact_summary_on_mentions_that_have_one(
    client: TestClient[Litestar], db_session: Session
) -> None:
    catalogue = _catalogue(db_session)
    candidate = _candidate(db_session, catalogue, key="personalausweis")
    snapshot = _artifact(db_session, catalogue)
    _mention(db_session, candidate, catalogue, "with-artifact", artifact=snapshot)
    _mention(db_session, candidate, catalogue, "without-artifact")

    body = client.get(f"{CANDIDATES_URL}/{candidate.id}", headers=_auth()).json()

    by_field = {row["source_field"]: row for row in body["mentions"]}
    assert by_field["with-artifact"]["artifact"] == {
        "id": str(snapshot.id),
        "kind": "html_snapshot",
        "fetched_at": "2026-10-26T12:00:00Z",
    }
    assert by_field["with-artifact"]["artifact_id"] == str(snapshot.id)
    assert by_field["without-artifact"]["artifact"] is None


def test_admin_candidate_detail_includes_the_jurisdiction_name(
    client: TestClient[Litestar], db_session: Session
) -> None:
    catalogue = _catalogue(db_session)
    candidate = _candidate(db_session, catalogue, key="personalausweis")

    body = client.get(f"{CANDIDATES_URL}/{candidate.id}", headers=_auth()).json()

    assert body["jurisdiction_name_i18n"] == {"en": "Testland"}
