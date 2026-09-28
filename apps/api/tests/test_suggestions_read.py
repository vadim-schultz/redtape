"""HTTP behavior of `GET /api/v1/suggestions` and `GET /api/v1/suggestions/{id}` (Chapter 7)."""

from __future__ import annotations

import uuid
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest
from app.main import create_app
from app.models.api_key import ApiKey
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.suggestion import Suggestion, SuggestionKind, SuggestionSource, SuggestionStatus
from app.models.user import AppUser
from app.url_normalization import normalize_url
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

URL = "/api/v1/suggestions"


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    monkeypatch.setattr("app.main.provide_session", lambda: db_session)
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def country(db_session: Session) -> Jurisdiction:
    jurisdiction = Jurisdiction(
        kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Testland"}, code=f"T{uuid.uuid4().hex[:8]}"
    )
    db_session.add(jurisdiction)
    db_session.flush()
    return jurisdiction


@pytest.fixture
def other_country(db_session: Session) -> Jurisdiction:
    jurisdiction = Jurisdiction(
        kind=JurisdictionKind.COUNTRY, name_i18n={"en": "Otherland"}, code=f"O{uuid.uuid4().hex[:8]}"
    )
    db_session.add(jurisdiction)
    db_session.flush()
    return jurisdiction


def _make_suggestion(
    db_session: Session,
    jurisdiction: Jurisdiction,
    *,
    kind: SuggestionKind = SuggestionKind.NEW_DOCUMENT,
    status: SuggestionStatus = SuggestionStatus.PENDING,
    source_type: SuggestionSource = SuggestionSource.HUMAN,
    submitted_by_user_id: uuid.UUID | None = None,
    submitted_by_api_key_id: uuid.UUID | None = None,
    created_at: datetime | None = None,
) -> Suggestion:
    official_url = f"https://example.gov/{uuid.uuid4().hex[:12]}"
    row = Suggestion(
        kind=kind,
        status=status,
        source_type=source_type,
        jurisdiction_id=jurisdiction.id,
        payload={"title_i18n": {"en": "A document"}, "official_url": official_url},
        normalized_url=normalize_url(official_url),
        submitted_by_user_id=submitted_by_user_id,
        submitted_by_api_key_id=submitted_by_api_key_id,
        created_at=created_at or datetime.now(UTC),
    )
    db_session.add(row)
    db_session.flush()
    return row


def _make_user(db_session: Session, *, display_name: str | None = "Ada", email: str | None = None) -> AppUser:
    row = AppUser(id=uuid.uuid4(), email=email or f"{uuid.uuid4().hex}@example.com", display_name=display_name)
    db_session.add(row)
    db_session.flush()
    return row


def _make_api_key(db_session: Session, *, name: str = "crawler-de-federal") -> ApiKey:
    row = ApiKey(name=name, key_hash=uuid.uuid4().hex, key_prefix=uuid.uuid4().hex[:8])
    db_session.add(row)
    db_session.flush()
    return row


@contextmanager
def _count_queries(db_session: Session) -> Generator[dict[str, int], None, None]:
    counter = {"n": 0}
    connection = db_session.connection()

    def _before_cursor_execute(*_args: object, **_kwargs: object) -> None:
        counter["n"] += 1

    event.listen(connection, "before_cursor_execute", _before_cursor_execute)
    try:
        yield counter
    finally:
        event.remove(connection, "before_cursor_execute", _before_cursor_execute)


def test_lists_newest_first(client: TestClient[Litestar], db_session: Session, country: Jurisdiction) -> None:
    now = datetime.now(UTC)
    oldest = _make_suggestion(db_session, country, created_at=now - timedelta(minutes=2))
    newest = _make_suggestion(db_session, country, created_at=now)
    middle = _make_suggestion(db_session, country, created_at=now - timedelta(minutes=1))

    response = client.get(URL)

    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(newest.id), str(middle.id), str(oldest.id)]


def test_paginates_with_total_offset_and_limit(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction
) -> None:
    for _ in range(25):
        _make_suggestion(db_session, country)

    first_page = client.get(URL, params={"offset": 0, "limit": 20})
    second_page = client.get(URL, params={"offset": 20, "limit": 20})

    assert len(first_page.json()["items"]) == 20
    assert first_page.json()["total"] == 25
    assert len(second_page.json()["items"]) == 5
    assert second_page.json()["total"] == 25
    first_ids = {item["id"] for item in first_page.json()["items"]}
    second_ids = {item["id"] for item in second_page.json()["items"]}
    assert first_ids.isdisjoint(second_ids)


def test_filters_by_status(client: TestClient[Litestar], db_session: Session, country: Jurisdiction) -> None:
    pending = _make_suggestion(db_session, country, status=SuggestionStatus.PENDING)
    _make_suggestion(db_session, country, status=SuggestionStatus.APPROVED)

    response = client.get(URL, params={"status": "pending"})

    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(pending.id)]


def test_accepts_several_statuses(client: TestClient[Litestar], db_session: Session, country: Jurisdiction) -> None:
    pending = _make_suggestion(db_session, country, status=SuggestionStatus.PENDING)
    approved = _make_suggestion(db_session, country, status=SuggestionStatus.APPROVED)
    _make_suggestion(db_session, country, status=SuggestionStatus.REJECTED)

    response = client.get(URL, params=[("status", "pending"), ("status", "approved")])

    ids = {item["id"] for item in response.json()["items"]}
    assert ids == {str(pending.id), str(approved.id)}


def test_filters_by_kind(client: TestClient[Litestar], db_session: Session, country: Jurisdiction) -> None:
    new_document = _make_suggestion(db_session, country, kind=SuggestionKind.NEW_DOCUMENT)
    _make_suggestion(db_session, country, kind=SuggestionKind.NEW_REQUIREMENT)

    response = client.get(URL, params={"kind": "new_document"})

    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(new_document.id)]


def test_filters_by_source_type(client: TestClient[Litestar], db_session: Session, country: Jurisdiction) -> None:
    crawler = _make_suggestion(db_session, country, source_type=SuggestionSource.CRAWLER)
    _make_suggestion(db_session, country, source_type=SuggestionSource.HUMAN)

    response = client.get(URL, params={"source_type": "crawler"})

    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(crawler.id)]


def test_filters_by_jurisdiction_id(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction, other_country: Jurisdiction
) -> None:
    in_scope = _make_suggestion(db_session, country)
    _make_suggestion(db_session, other_country)

    response = client.get(URL, params={"jurisdiction_id": str(country.id)})

    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(in_scope.id)]


def test_rejects_an_unknown_status_with_422(client: TestClient[Litestar]) -> None:
    response = client.get(URL, params={"status": "bogus"})

    assert response.status_code == 422


@pytest.mark.parametrize("limit", [0, 101])
def test_rejects_limit_0_and_101(client: TestClient[Litestar], limit: int) -> None:
    response = client.get(URL, params={"limit": limit})

    assert response.status_code == 422


def test_needs_no_authentication(client: TestClient[Litestar]) -> None:
    response = client.get(URL)

    assert response.status_code == 200


def test_never_exposes_emails_or_key_hashes(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction
) -> None:
    user = _make_user(db_session, email="secret-address@example.com")
    key = _make_api_key(db_session)
    _make_suggestion(db_session, country, submitted_by_user_id=user.id)
    _make_suggestion(db_session, country, source_type=SuggestionSource.CRAWLER, submitted_by_api_key_id=key.id)

    response = client.get(URL)

    assert "secret-address@example.com" not in response.text
    assert key.key_hash not in response.text


def test_lists_with_a_constant_number_of_queries(
    client: TestClient[Litestar], db_session: Session, country: Jurisdiction
) -> None:
    for _ in range(3):
        _make_suggestion(db_session, country)
    with _count_queries(db_session) as small:
        client.get(URL)

    for _ in range(10):
        _make_suggestion(db_session, country)
    with _count_queries(db_session) as large:
        client.get(URL)

    assert small["n"] == large["n"]


def test_returns_the_suggestion(client: TestClient[Litestar], db_session: Session, country: Jurisdiction) -> None:
    user = _make_user(db_session, display_name="Ada Lovelace")
    suggestion = _make_suggestion(db_session, country, submitted_by_user_id=user.id)

    response = client.get(f"{URL}/{suggestion.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(suggestion.id)
    assert body["submitted_by"] == {"kind": "user", "display_name": "Ada Lovelace"}


def test_unknown_id_returns_404(client: TestClient[Litestar]) -> None:
    response = client.get(f"{URL}/{uuid.uuid4()}")

    assert response.status_code == 404


def test_malformed_id_returns_404(client: TestClient[Litestar]) -> None:
    """Litestar's `:uuid` path type fails to match a non-UUID segment, so the route itself 404s."""
    response = client.get(f"{URL}/not-a-uuid")

    assert response.status_code == 404
