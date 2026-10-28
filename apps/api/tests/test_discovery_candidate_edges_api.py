"""Machine edge batch route and the admin edge read (extraction chapter E1, loop C)."""

from __future__ import annotations

import uuid

import pytest
from app.models.discovery import (
    CatalogueService,
    DiscoveryCandidateEdge,
    DiscoveryDocumentCandidate,
    DiscoveryEdgeBasis,
)
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from test_db_headroom import LIMIT, SizeProbe, probe  # noqa: F401
from test_discovery_admin_api import _catalogue, client  # noqa: F401
from test_discovery_candidates_admin_api import CANDIDATES_URL, _auth
from test_discovery_machine_api import _issue_key

EDGES_URL = "/api/v1/discovery/machine/candidates/edges"


def _candidate(db_session: Session, catalogue: CatalogueService, key: str) -> DiscoveryDocumentCandidate:
    row = DiscoveryDocumentCandidate(jurisdiction_id=catalogue.jurisdiction_id, key=key, title_i18n={"de": key.title()})
    db_session.add(row)
    db_session.flush()
    return row


def _item(catalogue: CatalogueService, parent: str, required: str, **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "catalogue_service_id": str(catalogue.id),
        "parent_title_i18n": {"de": parent},
        "required_title_i18n": {"de": required},
        "basis": "explicit",
        "excerpt": "Zum Antrag bringen Sie die Meldebescheinigung mit.",
        "extractor": "llm",
        "extractor_version": "1",
    }
    body.update(overrides)
    return body


def _post(client: TestClient[Litestar], key: str, *items: dict[str, object]):  # noqa: F811
    return client.post(EDGES_URL, json={"items": list(items)}, headers={"X-API-Key": key})


def _edge_count(db_session: Session) -> int:
    return int(db_session.scalar(select(func.count()).select_from(DiscoveryCandidateEdge)) or 0)


@pytest.fixture
def procedure(db_session: Session) -> CatalogueService:
    catalogue = _catalogue(db_session)
    _candidate(db_session, catalogue, "reisepass")
    _candidate(db_session, catalogue, "meldebescheinigung")
    _candidate(db_session, catalogue, "passfoto")
    return catalogue


def test_edge_batch_creates_edges_between_existing_candidates_and_reports_counts(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
    procedure: CatalogueService,
) -> None:
    key = _issue_key(db_session)

    response = _post(
        client,
        key,
        _item(procedure, "Reisepass", "Meldebescheinigung", condition="bei Zuzug", is_optional=True),
        _item(procedure, "Reisepass", "Passfoto", basis="derived_single_issued"),
    )

    assert response.status_code == 200
    assert response.json() == {"edges_created": 2, "edges_updated": 0, "edges_skipped": 0, "skipped": []}
    edges = {e.required_candidate_id: e for e in db_session.scalars(select(DiscoveryCandidateEdge))}
    assert len(edges) == 2
    assert {e.basis for e in edges.values()} == {DiscoveryEdgeBasis.EXPLICIT, DiscoveryEdgeBasis.DERIVED_SINGLE_ISSUED}
    explicit = next(e for e in edges.values() if e.basis is DiscoveryEdgeBasis.EXPLICIT)
    assert (explicit.condition, explicit.is_optional) == ("bei Zuzug", True)


def test_an_edge_with_an_unknown_endpoint_is_skipped_with_a_reason_and_does_not_fail_the_batch(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
    procedure: CatalogueService,
) -> None:
    key = _issue_key(db_session)

    response = _post(
        client,
        key,
        _item(procedure, "Reisepass", "Meldebescheinigung"),
        _item(procedure, "Reisepass", "Unbekannt"),
        _item(procedure, "Unbekannt", "Passfoto"),
        _item(procedure, "Reisepass", "!!!"),
    )

    assert response.status_code == 200
    assert response.json() == {
        "edges_created": 1,
        "edges_updated": 0,
        "edges_skipped": 3,
        "skipped": [
            {"index": 1, "reason": "unknown_required"},
            {"index": 2, "reason": "unknown_parent"},
            {"index": 3, "reason": "unknown_required"},
        ],
    }
    assert _edge_count(db_session) == 1


def test_an_equal_endpoint_edge_is_skipped_and_a_blank_excerpt_too(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
    procedure: CatalogueService,
) -> None:
    key = _issue_key(db_session)

    response = _post(
        client,
        key,
        _item(procedure, "Reisepass", " REISEPASS "),
        _item(procedure, "Reisepass", "Passfoto", excerpt="   "),
    )

    assert response.json()["skipped"] == [
        {"index": 0, "reason": "same_endpoints"},
        {"index": 1, "reason": "blank_excerpt"},
    ]
    assert _edge_count(db_session) == 0


def test_a_replayed_edge_updates_in_place(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
    procedure: CatalogueService,
) -> None:
    key = _issue_key(db_session)
    _post(client, key, _item(procedure, "Reisepass", "Passfoto", condition="alt"))

    replay = _post(
        client, key, _item(procedure, "Reisepass", "Passfoto", condition=None, excerpt="Neu", extractor_version="2")
    )

    assert replay.json() == {"edges_created": 0, "edges_updated": 1, "edges_skipped": 0, "skipped": []}
    db_session.expire_all()
    edge = db_session.scalars(select(DiscoveryCandidateEdge)).one()
    assert (edge.condition, edge.excerpt, edge.extractor_version) == (None, "Neu", "2")


def test_a_batch_with_an_unknown_catalogue_row_is_rejected_whole(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
    procedure: CatalogueService,
) -> None:
    key = _issue_key(db_session)

    response = _post(
        client,
        key,
        _item(procedure, "Reisepass", "Passfoto"),
        _item(procedure, "Reisepass", "Passfoto", catalogue_service_id=str(uuid.uuid4())),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Catalogue service not found"
    assert _edge_count(db_session) == 0


def test_an_edge_batch_over_100_items_is_a_422(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
    procedure: CatalogueService,
) -> None:
    key = _issue_key(db_session)

    response = _post(client, key, *[_item(procedure, "Reisepass", "Passfoto")] * 101)

    assert response.status_code == 422


def test_the_edge_batch_requires_the_machine_key_and_is_refused_with_507_above_the_limit(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
    procedure: CatalogueService,
    probe: SizeProbe,  # noqa: F811
) -> None:
    key = _issue_key(db_session)
    body = {"items": [_item(procedure, "Reisepass", "Passfoto")]}

    anonymous = client.post(EDGES_URL, json=body)
    probe.change_to(LIMIT + 1)
    refused = client.post(EDGES_URL, json=body, headers={"X-API-Key": key})

    assert anonymous.status_code == 401
    assert (refused.status_code, refused.json()["detail"]) == (507, "database_soft_limit")
    assert _edge_count(db_session) == 0


def test_admin_edges_lists_parent_required_procedure_and_basis(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
    procedure: CatalogueService,
) -> None:
    _post(client, _issue_key(db_session), _item(procedure, "Reisepass", "Meldebescheinigung", condition="bei Zuzug"))
    parent = db_session.scalars(
        select(DiscoveryDocumentCandidate).where(DiscoveryDocumentCandidate.key == "reisepass")
    ).one()
    required = db_session.scalars(
        select(DiscoveryDocumentCandidate).where(DiscoveryDocumentCandidate.key == "meldebescheinigung")
    ).one()

    from_parent = client.get(f"{CANDIDATES_URL}/{parent.id}/edges", headers=_auth())
    from_required = client.get(f"{CANDIDATES_URL}/{required.id}/edges", headers=_auth())

    assert from_parent.status_code == 200
    assert from_parent.json() == from_required.json()
    (item,) = from_parent.json()["items"]
    assert item["parent_candidate_id"] == str(parent.id)
    assert item["parent_title_i18n"] == {"de": "Reisepass"}
    assert item["required_candidate_id"] == str(required.id)
    assert item["required_title_i18n"] == {"de": "Meldebescheinigung"}
    assert (item["basis"], item["condition"]) == ("explicit", "bei Zuzug")
    assert item["catalogue_service_id"] == str(procedure.id)
    assert item["procedure_title_i18n"] == {"de": "Leistung"}


def test_admin_edges_of_an_unknown_candidate_is_404_and_needs_an_admin(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
    procedure: CatalogueService,
) -> None:
    unknown = f"{CANDIDATES_URL}/{uuid.uuid4()}/edges"
    known = _candidate(db_session, procedure, "lichtbild")

    assert client.get(unknown, headers=_auth()).status_code == 404
    assert client.get(f"{CANDIDATES_URL}/{known.id}/edges").status_code == 401
