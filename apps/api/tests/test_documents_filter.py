from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from app.main import create_app
from app.models.document import Document
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.taxonomy import Category, Domain, LifeSituation, document_life_situation
from httpx import Response
from litestar import Litestar
from litestar.testing import TestClient
from scripts.seed_taxonomy import seed_taxonomy
from sqlalchemy import select, update
from sqlalchemy.orm import Session

URL = "/api/v1/documents"


def _term(session: Session, model: type[Domain] | type[LifeSituation], code: str):
    return session.scalars(select(model).where(model.code == code)).one()


def _document(session: Session, jurisdiction_id: uuid.UUID, slug: str, domains=(), situations=()) -> Document:
    doc = Document(
        jurisdiction_id=jurisdiction_id,
        slug=slug,
        title_i18n={"de": slug},
        description_i18n={"de": ""},
        domains=[_term(session, Domain, code) for code in domains],
        life_situations=[_term(session, LifeSituation, code) for code in situations],
    )
    session.add(doc)
    return doc


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    # tags={}: this suite tags its own documents directly (see `_document` above); the
    # default tag map references a document graph this fixture never seeds.
    seed_taxonomy(db_session)
    country = Jurisdiction(
        kind=JurisdictionKind.COUNTRY,
        code="XX",
        administrative_roles=["COUNTRY"],
        name_i18n={"de": "Testland"},
        multiple_postal_codes=False,
        last_updated=datetime.now(UTC),
    )
    db_session.add(country)
    db_session.flush()
    housing, moving = "housing", "moving-house"
    other_domain = _other_code(db_session, Domain, housing)
    other_situation = _other_code(db_session, LifeSituation, moving)
    _document(db_session, country.id, "a-housing-moving", [housing], [moving])
    _document(db_session, country.id, "b-housing-other", [housing], [other_situation])
    _document(db_session, country.id, "c-other-moving", [other_domain], [moving])
    _document(db_session, country.id, "d-untagged")
    db_session.flush()
    monkeypatch.setattr("app.main.provide_session", lambda: db_session)
    app = create_app()
    with TestClient(app) as test_client:
        test_client.other_domain = other_domain  # type: ignore[attr-defined]
        test_client.jurisdiction_id = str(country.id)  # type: ignore[attr-defined]
        yield test_client


def _other_code(session: Session, model: type[Domain] | type[LifeSituation], excluded: str) -> str:
    return session.scalars(select(model.code).where(model.code != excluded).order_by(model.code)).first()


def _get(client: TestClient[Litestar], params: dict | list) -> Response:
    """List documents scoped to the test jurisdiction so seeded catalog rows never leak in."""
    scope = [("jurisdiction_id", client.jurisdiction_id)]  # type: ignore[attr-defined]
    pairs = list(params.items()) if isinstance(params, dict) else params
    return client.get(URL, params=scope + pairs)


def _slugs(response) -> list[str]:
    return [item["slug"] for item in response.json()["items"]]


def test_domain_returns_only_documents_tagged_with_it(client: TestClient[Litestar]) -> None:
    assert _slugs(_get(client, {"domain": "housing"})) == ["a-housing-moving", "b-housing-other"]


def test_domain_and_situation_are_anded(client: TestClient[Litestar]) -> None:
    response = _get(client, {"domain": "housing", "situation": "moving-house"})

    assert _slugs(response) == ["a-housing-moving"]


def test_two_domains_are_ored(client: TestClient[Litestar]) -> None:
    params = [("domain", "housing"), ("domain", client.other_domain)]  # type: ignore[attr-defined]

    assert _slugs(_get(client, params)) == ["a-housing-moving", "b-housing-other", "c-other-moving"]


def test_total_reflects_the_filter_not_the_catalog(client: TestClient[Litestar]) -> None:
    body = _get(client, {"domain": "housing", "limit": 1}).json()

    assert body["total"] == 2
    assert len(body["items"]) == 1


def test_unknown_domain_code_returns_422(client: TestClient[Litestar]) -> None:
    assert _get(client, {"domain": "nope"}).status_code == 422


def test_unknown_situation_code_returns_422(client: TestClient[Litestar]) -> None:
    assert _get(client, {"situation": "nope"}).status_code == 422


def test_situation_alone_returns_every_document_with_it_across_domains(client: TestClient[Litestar]) -> None:
    assert _slugs(_get(client, {"situation": "moving-house"})) == ["a-housing-moving", "c-other-moving"]


def test_no_params_returns_the_unfiltered_list(client: TestClient[Litestar]) -> None:
    body = _get(client, {}).json()

    assert body["total"] == 4
    assert len(body["items"]) == 4


def test_untagged_document_never_appears_when_a_filter_is_set(client: TestClient[Litestar]) -> None:
    for params in ({"domain": "housing"}, {"situation": "moving-house"}):
        assert "d-untagged" not in _slugs(_get(client, params))


def test_category_root_filter_includes_direct_and_descendant_category_links(
    client: TestClient[Litestar], db_session: Session
) -> None:
    country_id = uuid.UUID(client.jurisdiction_id)  # type: ignore[attr-defined]
    root = db_session.scalars(select(Category).where(Category.code == "home-and-housing")).one()
    child = db_session.scalars(select(Category).where(Category.code == "moving-house")).one()
    db_session.add_all(
        [
            Document(
                jurisdiction_id=country_id,
                slug="canonical-root",
                title_i18n={"de": "canonical-root"},
                description_i18n={"de": ""},
                categories=[root],
            ),
            Document(
                jurisdiction_id=country_id,
                slug="canonical-child",
                title_i18n={"de": "canonical-child"},
                description_i18n={"de": ""},
                categories=[child],
            ),
        ]
    )
    db_session.flush()

    assert _slugs(_get(client, {"category": "home-and-housing"})) == ["canonical-child", "canonical-root"]


def test_unknown_category_code_returns_422(client: TestClient[Litestar]) -> None:
    response = _get(client, {"category": "not-a-category"})

    assert response.status_code == 422
    assert "Unknown category code" in response.json()["detail"]


def test_conflicting_legacy_group_and_situation_returns_diagnostic_422(
    client: TestClient[Litestar],
) -> None:
    response = _get(client, {"group": "family-relationships", "situation": "moving-house"})

    assert response.status_code == 422
    assert "conflicting legacy taxonomy filters" in response.json()["detail"].lower()


def test_available_leaf_codes_is_empty_without_a_situation_filter(client: TestClient[Litestar]) -> None:
    assert _get(client, {}).json()["available_leaf_codes"] == []


def test_available_leaf_codes_includes_the_leaf_codes_in_scope_for_the_selected_situation(
    client: TestClient[Litestar], db_session: Session
) -> None:
    moving_house_id = _term(db_session, LifeSituation, "moving-house").id
    db_session.execute(
        update(document_life_situation)
        .where(document_life_situation.c.life_situation_id == moving_house_id)
        .values(pvog_leaf_code="1050200")
    )
    db_session.flush()

    body = _get(client, {"situation": "moving-house"}).json()

    assert body["available_leaf_codes"] == ["1050200"]


def _detail(client: TestClient[Litestar], slug: str, locale: str = "en") -> dict:
    doc_id = next(i["id"] for i in _get(client, {"limit": 100}).json()["items"] if i["slug"] == slug)
    return client.get(f"{URL}/{doc_id}", headers={"Accept-Language": locale}).json()


def test_detail_includes_resolved_domains_and_life_situations(client: TestClient[Litestar]) -> None:
    body = _detail(client, "a-housing-moving")

    assert [d["code"] for d in body["domains"]] == ["housing"]
    assert [s["code"] for s in body["life_situations"]] == ["moving-house"]
    assert set(body["domains"][0]) == {"code", "name", "description", "icon", "confidence"}
    assert body["domains"][0]["name"] != "housing"
    assert body["domains"][0]["confidence"] == 1.0


def test_detail_includes_canonical_category_tags_with_confidence(
    client: TestClient[Litestar], db_session: Session
) -> None:
    document_id = next(
        item["id"] for item in _get(client, {"limit": 100}).json()["items"] if item["slug"] == "a-housing-moving"
    )
    document = db_session.get(Document, uuid.UUID(document_id))
    assert document is not None
    child = db_session.scalars(select(Category).where(Category.code == "moving-house")).one()
    document.categories.append(child)
    db_session.flush()

    body = _detail(client, "a-housing-moving")

    assert [(tag["code"], tag["confidence"]) for tag in body["categories"]] == [("moving-house", 1.0)]


def test_detail_document_without_tags_returns_empty_arrays(client: TestClient[Litestar]) -> None:
    body = _detail(client, "d-untagged")

    assert body["domains"] == []
    assert body["life_situations"] == []
