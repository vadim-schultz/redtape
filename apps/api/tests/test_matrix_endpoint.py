from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from app.main import create_app
from app.models.document import Document
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.taxonomy import Domain, LifeSituation
from litestar import Litestar
from litestar.testing import TestClient
from scripts.seed_taxonomy import seed_taxonomy
from sqlalchemy import select
from sqlalchemy.orm import Session

URL = "/api/v1/matrix"
HOUSING, MOVING = "housing", "moving-house"


def _term(session: Session, model: type[Domain] | type[LifeSituation], code: str):
    return session.scalars(select(model).where(model.code == code)).one()


def _other_code(session: Session, model: type[Domain] | type[LifeSituation], excluded: str) -> str:
    return session.scalars(select(model.code).where(model.code != excluded).order_by(model.code)).first()


def _country(session: Session, code: str) -> Jurisdiction:
    country = Jurisdiction(
        kind=JurisdictionKind.COUNTRY,
        code=code,
        administrative_roles=["COUNTRY"],
        name_i18n={"de": code},
        multiple_postal_codes=False,
        last_updated=datetime.now(UTC),
    )
    session.add(country)
    session.flush()
    return country


def _document(session: Session, jurisdiction_id: uuid.UUID, slug: str, domains=(), situations=()) -> None:
    session.add(
        Document(
            jurisdiction_id=jurisdiction_id,
            slug=slug,
            title_i18n={"de": slug},
            description_i18n={"de": ""},
            domains=[_term(session, Domain, code) for code in domains],
            life_situations=[_term(session, LifeSituation, code) for code in situations],
        )
    )


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    # tags={}: this suite tags its own documents directly (see `_document` above); the
    # default tag map references a document graph this fixture never seeds.
    seed_taxonomy(db_session, tags={})
    home, abroad = _country(db_session, "XX"), _country(db_session, "YY")
    other_d = _other_code(db_session, Domain, HOUSING)
    other_s = _other_code(db_session, LifeSituation, MOVING)
    _document(db_session, home.id, "a", [HOUSING, other_d], [MOVING, other_s])
    _document(db_session, home.id, "b", [HOUSING], [other_s])
    _document(db_session, home.id, "c", [other_d], [MOVING])
    _document(db_session, home.id, "d-untagged")
    _document(db_session, abroad.id, "e", [HOUSING], [MOVING])
    db_session.flush()
    monkeypatch.setattr("app.main.provide_session", lambda: db_session)
    with TestClient(create_app()) as test_client:
        test_client.home = str(home.id)  # type: ignore[attr-defined]
        test_client.abroad = str(abroad.id)  # type: ignore[attr-defined]
        test_client.other_d = other_d  # type: ignore[attr-defined]
        test_client.other_s = other_s  # type: ignore[attr-defined]
        yield test_client


def _matrix(client: TestClient[Litestar], jurisdiction_id: str) -> dict:
    return client.get(URL, params={"jurisdiction_id": jurisdiction_id}).json()


def _cells(body: dict) -> dict[tuple[str, str], int]:
    return {(c["domain"], c["situation"]): c["count"] for c in body["cells"]}


def _counts(entries: list[dict]) -> dict[str, int]:
    return {e["code"]: e["count"] for e in entries}


def test_counts_documents_per_domain_and_situation_pair(client: TestClient[Litestar]) -> None:
    cells = _cells(_matrix(client, client.home))  # type: ignore[attr-defined]

    assert cells[(HOUSING, MOVING)] == 1
    assert cells[(HOUSING, client.other_s)] == 2  # type: ignore[attr-defined]
    assert cells[(client.other_d, MOVING)] == 2  # type: ignore[attr-defined]


def test_document_with_two_domains_counts_once_per_cell(client: TestClient[Litestar]) -> None:
    cells = _cells(_matrix(client, client.home))  # type: ignore[attr-defined]

    assert sum(cells.values()) == 6  # a occupies four cells, b two, c two: 1+2+2+1
    assert max(cells.values()) == 2


def test_omits_empty_cells(client: TestClient[Litestar]) -> None:
    cells = _cells(_matrix(client, client.abroad))  # type: ignore[attr-defined]

    assert cells == {(HOUSING, MOVING): 1}


def test_untagged_document_contributes_nothing(client: TestClient[Litestar]) -> None:
    body = _matrix(client, client.home)  # type: ignore[attr-defined]

    assert body["total"] == 4
    assert max(_counts(body["domains"]).values()) == 2


def test_unknown_jurisdiction_returns_empty_cells_not_an_error(client: TestClient[Litestar]) -> None:
    response = client.get(URL, params={"jurisdiction_id": str(uuid.uuid4())})

    assert response.status_code == 200
    assert response.json() == {"total": 0, "cells": [], "situations": [], "domains": []}


def test_unknown_municipality_returns_empty_matrix(client: TestClient[Litestar]) -> None:
    response = client.get(URL, params={"municipality_code": "no-such-code"})

    assert response.status_code == 200
    assert response.json()["cells"] == []


def test_codes_and_order_follow_taxonomy_sort_order(client: TestClient[Litestar]) -> None:
    domains = [d["code"] for d in client.get("/api/v1/domains").json()]
    situations = [s["code"] for s in client.get("/api/v1/life-situations").json()]
    body = _matrix(client, client.home)  # type: ignore[attr-defined]

    keys = [(c["domain"], c["situation"]) for c in body["cells"]]
    assert keys == sorted(keys, key=lambda k: (domains.index(k[0]), situations.index(k[1])))


def test_situation_total_counts_each_document_once_across_domains(client: TestClient[Litestar]) -> None:
    body = _matrix(client, client.home)  # type: ignore[attr-defined]
    row_cells = sum(n for (_, s), n in _cells(body).items() if s == MOVING)

    assert _counts(body["situations"])[MOVING] == 2
    assert row_cells == 3


def test_domain_total_counts_each_document_once_across_situations(client: TestClient[Litestar]) -> None:
    body = _matrix(client, client.home)  # type: ignore[attr-defined]
    column_cells = sum(n for (d, _), n in _cells(body).items() if d == HOUSING)

    assert _counts(body["domains"])[HOUSING] == 2
    assert column_cells == 3


def test_axis_total_equals_documents_endpoint_total_for_the_same_filter(client: TestClient[Litestar]) -> None:
    body = _matrix(client, client.home)  # type: ignore[attr-defined]
    scope = {"jurisdiction_id": client.home}  # type: ignore[attr-defined]

    by_domain = client.get("/api/v1/documents", params={**scope, "domain": HOUSING}).json()["total"]
    by_situation = client.get("/api/v1/documents", params={**scope, "situation": MOVING}).json()["total"]
    assert _counts(body["domains"])[HOUSING] == by_domain
    assert _counts(body["situations"])[MOVING] == by_situation


def test_total_includes_untagged_documents(client: TestClient[Litestar]) -> None:
    body = _matrix(client, client.home)  # type: ignore[attr-defined]

    assert body["total"] > max(_counts(body["domains"]).values())


def test_jurisdiction_scope_excludes_other_jurisdictions(client: TestClient[Litestar]) -> None:
    body = _matrix(client, client.abroad)  # type: ignore[attr-defined]

    assert body["total"] == 1
    assert _counts(body["domains"]) == {HOUSING: 1}


def test_terms_without_documents_in_scope_are_omitted(client: TestClient[Litestar]) -> None:
    body = _matrix(client, client.abroad)  # type: ignore[attr-defined]

    assert _counts(body["situations"]) == {MOVING: 1}
    assert client.other_d not in _counts(body["domains"])  # type: ignore[attr-defined]
