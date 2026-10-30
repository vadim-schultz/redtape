"""``GET /machine/candidates/sources``: catalogue rows with candidate mentions and their newest snapshot (chapter 1)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.models.discovery import (
    CatalogueService,
    DiscoveryArtifact,
    DiscoveryArtifactKind,
    DiscoveryDocumentCandidate,
)
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy.orm import Session

from test_discovery_admin_api import _catalogue
from test_discovery_candidates_admin_api import _candidate, _mention
from test_discovery_machine_api import _issue_key, client  # noqa: F401

SOURCES_URL = "/api/v1/discovery/machine/candidates/sources"
FETCHED_AT = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)


def _artifact(
    db_session: Session,
    catalogue: CatalogueService,
    *,
    url: str = "https://portal.example/page",
    kind: DiscoveryArtifactKind = DiscoveryArtifactKind.HTML_SNAPSHOT,
    age_days: int = 0,
) -> DiscoveryArtifact:
    sha = uuid.uuid4().hex + uuid.uuid4().hex
    row = DiscoveryArtifact(
        catalogue_service_id=catalogue.id,
        kind=kind,
        storage_key=f"discovery/{catalogue.id}/{kind.value}/{sha}",
        sha256=sha,
        content_type="text/html" if kind is DiscoveryArtifactKind.HTML_SNAPSHOT else "image/jpeg",
        byte_size=10,
        source_url=url,
        fetched_at=FETCHED_AT - timedelta(days=age_days),
    )
    db_session.add(row)
    db_session.flush()
    return row


def _row(
    db_session: Session,
    external_id: str,
    *,
    mentions: int = 1,
    url: str | None = None,
    screenshot: bool = False,
    candidate: DiscoveryDocumentCandidate | None = None,
) -> CatalogueService:
    """A catalogue row with a snapshot, ``mentions`` mentions of one candidate, and optionally a screenshot."""
    row = _catalogue(db_session, external_id=external_id)
    target = url or f"https://portal.example/{external_id}"
    _artifact(db_session, row, url=target)
    named = candidate or _candidate(db_session, row, key=f"doc-{external_id}")
    for n in range(mentions):
        _mention(db_session, named, row, f"field[{n}]")
    if screenshot:
        _artifact(db_session, row, url=target, kind=DiscoveryArtifactKind.SCREENSHOT)
    return row


def _get(client: TestClient[Litestar], key: str, **params: object):  # noqa: F811
    return client.get(SOURCES_URL, params=params, headers={"X-API-Key": key})


def test_sources_lists_a_mentioned_row_with_its_newest_snapshot_url(
    client: TestClient[Litestar], db_session: Session  # noqa: F811
) -> None:
    """Two snapshots on one row: the newer source_url is returned with the right counts."""
    key = _issue_key(db_session)
    row = _row(db_session, "svc-1", mentions=2, url="https://portal.example/new")
    _artifact(db_session, row, url="https://old.example/page", age_days=3)

    body = _get(client, key).json()

    assert body["total"] == 1
    assert body["items"] == [
        {
            "catalogue_service_id": str(row.id),
            "source_url": "https://portal.example/new",
            "host": "portal.example",
            "has_screenshot": False,
            "mention_count": 2,
        }
    ]


def test_sources_missing_screenshot_hides_rows_that_have_a_screenshot(
    client: TestClient[Litestar], db_session: Session  # noqa: F811
) -> None:
    """Only the row without a screenshot survives ``missing=screenshot``; without it both are listed."""
    key = _issue_key(db_session)
    _row(db_session, "svc-shot", screenshot=True)
    bare = _row(db_session, "svc-bare")

    missing = _get(client, key, missing="screenshot").json()
    everything = _get(client, key).json()

    assert [(i["catalogue_service_id"], i["has_screenshot"]) for i in missing["items"]] == [(str(bare.id), False)]
    assert missing["total"] == 1
    assert sorted(i["has_screenshot"] for i in everything["items"]) == [False, True]


def test_sources_filters_by_host(client: TestClient[Litestar], db_session: Session) -> None:  # noqa: F811
    """Rows on two hosts: ``host=`` returns the one whose snapshot url has that host, case-insensitively."""
    key = _issue_key(db_session)
    wanted = _row(db_session, "svc-a", url="https://Portal.Example/a")
    _row(db_session, "svc-b", url="https://other.example/b")

    body = _get(client, key, host="portal.example").json()

    assert [i["catalogue_service_id"] for i in body["items"]] == [str(wanted.id)]
    assert (body["total"], _get(client, key, host="nowhere.example").json()["total"]) == (1, 0)


def test_sources_filters_by_candidate(client: TestClient[Litestar], db_session: Session) -> None:  # noqa: F811
    """``candidate_id=`` keeps the rows that mention it; unknown id is empty; a non-UUID is a 422."""
    key = _issue_key(db_session)
    first, second = _row(db_session, "svc-1"), _row(db_session, "svc-2")
    on_first = _candidate(db_session, first, key="only-first")
    _mention(db_session, on_first, first, "extra")

    body = _get(client, key, candidate_id=str(on_first.id)).json()

    assert [i["catalogue_service_id"] for i in body["items"]] == [str(first.id)]
    assert str(second.id) not in str(body)
    assert _get(client, key, candidate_id=str(uuid.uuid4())).json() == {"items": [], "total": 0, "offset": 0, "limit": 20}
    assert _get(client, key, candidate_id="not-a-uuid").status_code == 422


def test_sources_filters_by_catalogue_service_id(
    client: TestClient[Litestar], db_session: Session  # noqa: F811
) -> None:
    """Two of three rows by repeated ``catalogue_service_id``; a non-UUID or 21 ids are a 422."""
    key = _issue_key(db_session)
    rows = [_row(db_session, f"svc-{n}") for n in range(3)]

    ids = [str(rows[0].id), str(rows[2].id)]
    body = _get(client, key, catalogue_service_id=ids).json()

    assert sorted(i["catalogue_service_id"] for i in body["items"]) == sorted(ids)
    assert body["total"] == 2
    assert _get(client, key, catalogue_service_id="nope").status_code == 422
    assert _get(client, key, catalogue_service_id=[str(uuid.uuid4()) for _ in range(21)]).status_code == 422


def test_sources_omits_rows_without_a_mention_or_without_a_snapshot(
    client: TestClient[Litestar], db_session: Session  # noqa: F811
) -> None:
    """A snapshot with no mention and a mention with no snapshot are both absent."""
    key = _issue_key(db_session)
    kept = _row(db_session, "svc-kept")
    no_mention = _catalogue(db_session, external_id="svc-no-mention")
    _artifact(db_session, no_mention)
    no_snapshot = _catalogue(db_session, external_id="svc-no-snapshot")
    _mention(db_session, _candidate(db_session, no_snapshot, key="orphan"), no_snapshot)

    body = _get(client, key).json()

    assert [i["catalogue_service_id"] for i in body["items"]] == [str(kept.id)]
    assert body["total"] == 1


def test_sources_pages_deterministically(client: TestClient[Litestar], db_session: Session) -> None:  # noqa: F811
    """``limit=1`` over equal mention counts returns each row once across pages with a constant total."""
    key = _issue_key(db_session)
    rows = {str(_row(db_session, f"svc-{n}").id) for n in range(3)}

    pages = [_get(client, key, limit=1, offset=offset).json() for offset in range(3)]

    assert {p["total"] for p in pages} == {3}
    assert {p["items"][0]["catalogue_service_id"] for p in pages} == rows
    assert _get(client, key, limit=1, offset=3).json()["items"] == []


def test_sources_orders_by_mention_count_descending(
    client: TestClient[Litestar], db_session: Session  # noqa: F811
) -> None:
    """The busiest row comes first."""
    key = _issue_key(db_session)
    _row(db_session, "svc-few", mentions=1)
    busy = _row(db_session, "svc-busy", mentions=3)

    body = _get(client, key).json()

    assert body["items"][0]["catalogue_service_id"] == str(busy.id)


def test_sources_rejects_an_unknown_missing_value_and_a_bad_limit(
    client: TestClient[Litestar], db_session: Session  # noqa: F811
) -> None:
    """``missing=snapshot`` is a 422; ``limit=0`` and ``limit=101`` are rejected."""
    key = _issue_key(db_session)

    assert _get(client, key, missing="snapshot").status_code == 422
    assert _get(client, key, limit=0).status_code == 422
    assert _get(client, key, limit=101).status_code == 422


def test_sources_requires_the_machine_key(client: TestClient[Litestar], db_session: Session) -> None:  # noqa: F811
    """No key and a wrong key are both 401."""
    _issue_key(db_session)

    assert client.get(SOURCES_URL).status_code == 401
    assert client.get(SOURCES_URL, headers={"X-API-Key": "wrong"}).status_code == 401


def test_sources_path_is_not_shadowed_by_the_candidate_id_routes(
    client: TestClient[Litestar], db_session: Session  # noqa: F811
) -> None:
    """``/sources`` is served by the listing, not read as a candidate id (which would 404)."""
    key = _issue_key(db_session)

    assert _get(client, key).status_code == 200
