"""Machine route that records candidate mentions (chapter 6, loop C)."""

from __future__ import annotations

import uuid

import pytest
from app.models.discovery import (
    CatalogueService,
    DiscoveryCandidateMention,
    DiscoveryCandidateStatus,
    DiscoveryDocumentCandidate,
    DiscoveryMentionRole,
)
from litestar import Litestar
from litestar.testing import TestClient
from scripts.seed_taxonomy import seed_canonical_taxonomy
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from test_discovery_admin_api import _catalogue
from test_discovery_machine_api import _issue_key, client  # noqa: F401

MENTIONS_URL = "/api/v1/discovery/machine/candidates/mentions"


def _item(catalogue: CatalogueService, **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "catalogue_service_id": str(catalogue.id),
        "title_i18n": {"de": "Personalausweis"},
        "role": "required",
        "excerpt": "Bitte bringen Sie Ihren Personalausweis mit.",
        "source_field": "details[0]",
        "extractor": "pvog_payload",
        "extractor_version": "1",
    }
    body.update(overrides)
    return body


def _post(client: TestClient[Litestar], key: str, *items: dict[str, object]):  # noqa: F811
    return client.post(MENTIONS_URL, json={"items": list(items)}, headers={"X-API-Key": key})


def _count(db_session: Session, model: type) -> int:
    return int(db_session.scalar(select(func.count()).select_from(model)) or 0)


def test_mentions_batch_creates_a_candidate_and_a_mention(client: TestClient[Litestar], db_session: Session) -> None:  # noqa: F811
    key = _issue_key(db_session)
    catalogue = _catalogue(db_session)

    response = _post(client, key, _item(catalogue))

    assert response.status_code == 200
    assert response.json() == {
        "candidates_created": 1,
        "mentions_created": 1,
        "mentions_updated": 0,
        "unknown_codes": 0,
    }
    candidate = db_session.scalars(select(DiscoveryDocumentCandidate)).one()
    assert candidate.key == "personalausweis"
    assert candidate.jurisdiction_id == catalogue.jurisdiction_id
    assert candidate.status == DiscoveryCandidateStatus.STAGED


def test_mentions_batch_is_idempotent(client: TestClient[Litestar], db_session: Session) -> None:  # noqa: F811
    key = _issue_key(db_session)
    catalogue = _catalogue(db_session)
    _post(client, key, _item(catalogue))

    replay = _post(client, key, _item(catalogue, excerpt="Neuer Text", extractor_version="2"))

    assert replay.json() == {"candidates_created": 0, "mentions_created": 0, "mentions_updated": 1, "unknown_codes": 0}
    assert _count(db_session, DiscoveryDocumentCandidate) == 1
    mention = db_session.scalars(select(DiscoveryCandidateMention)).one()
    assert (mention.excerpt, mention.extractor_version) == ("Neuer Text", "2")


def test_two_services_mentioning_one_title_share_one_candidate(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    key = _issue_key(db_session)
    first = _catalogue(db_session, external_id="svc-a")
    second = _catalogue(db_session, external_id="svc-b")
    second.jurisdiction_id = first.jurisdiction_id
    db_session.flush()

    response = _post(client, key, _item(first), _item(second, title_i18n={"de": " PERSONALAUSWEIS "}))

    assert response.json() == {
        "candidates_created": 1,
        "mentions_created": 2,
        "mentions_updated": 0,
        "unknown_codes": 0,
    }
    assert _count(db_session, DiscoveryDocumentCandidate) == 1
    assert _count(db_session, DiscoveryCandidateMention) == 2


def test_same_title_in_two_jurisdictions_stays_two_candidates(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    key = _issue_key(db_session)
    first = _catalogue(db_session, external_id="svc-a")
    second = _catalogue(db_session, external_id="svc-b")

    _post(client, key, _item(first), _item(second))

    assert _count(db_session, DiscoveryDocumentCandidate) == 2


def test_title_locales_merge_without_overwriting(client: TestClient[Litestar], db_session: Session) -> None:  # noqa: F811
    key = _issue_key(db_session)
    catalogue = _catalogue(db_session)
    _post(client, key, _item(catalogue, title_i18n={"de": "Personalausweis"}))

    _post(client, key, _item(catalogue, title_i18n={"de": "Anderer Text", "en": "Personalausweis", "fr": "  "}))

    candidate = db_session.scalars(select(DiscoveryDocumentCandidate)).one()
    assert candidate.title_i18n == {"de": "Personalausweis", "en": "Personalausweis"}


def test_official_url_is_set_once(client: TestClient[Litestar], db_session: Session) -> None:  # noqa: F811
    key = _issue_key(db_session)
    catalogue = _catalogue(db_session)
    _post(client, key, _item(catalogue))
    _post(client, key, _item(catalogue, official_url="https://example.gov/id"))

    _post(client, key, _item(catalogue, official_url="https://example.gov/other"))

    candidate = db_session.scalars(select(DiscoveryDocumentCandidate)).one()
    assert candidate.official_url == "https://example.gov/id"


def test_an_emitted_candidate_keeps_its_status_but_accepts_mentions(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    key = _issue_key(db_session)
    catalogue = _catalogue(db_session)
    _post(client, key, _item(catalogue))
    candidate = db_session.scalars(select(DiscoveryDocumentCandidate)).one()
    candidate.status = DiscoveryCandidateStatus.EMITTED
    db_session.flush()

    response = _post(client, key, _item(catalogue, source_field="details[1]"))

    assert response.json()["mentions_created"] == 1
    db_session.refresh(candidate)
    assert candidate.status == DiscoveryCandidateStatus.EMITTED


def test_batch_with_an_unknown_catalogue_row_is_rejected_whole(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    key = _issue_key(db_session)
    catalogue = _catalogue(db_session)

    response = _post(client, key, _item(catalogue), _item(catalogue, catalogue_service_id=str(uuid.uuid4())))

    assert response.status_code == 404
    assert response.json()["detail"] == "Catalogue service not found"
    assert _count(db_session, DiscoveryDocumentCandidate) == 0
    assert _count(db_session, DiscoveryCandidateMention) == 0


def test_batch_with_an_unusable_title_is_rejected_whole(client: TestClient[Litestar], db_session: Session) -> None:  # noqa: F811
    key = _issue_key(db_session)
    catalogue = _catalogue(db_session)

    response = _post(client, key, _item(catalogue), _item(catalogue, title_i18n={"de": "!!!"}, source_field="x"))

    assert response.status_code == 422
    assert _count(db_session, DiscoveryDocumentCandidate) == 0


def test_batch_over_100_items_is_rejected(client: TestClient[Litestar], db_session: Session) -> None:  # noqa: F811
    key = _issue_key(db_session)
    catalogue = _catalogue(db_session)

    response = _post(client, key, *[_item(catalogue, source_field=f"f{n}") for n in range(101)])

    assert response.status_code == 422
    assert _count(db_session, DiscoveryCandidateMention) == 0


def test_batch_with_a_blank_title_is_rejected(client: TestClient[Litestar], db_session: Session) -> None:  # noqa: F811
    key = _issue_key(db_session)
    catalogue = _catalogue(db_session)

    response = _post(client, key, _item(catalogue, title_i18n={"de": "   "}))

    assert response.status_code == 422


def test_batch_of_exactly_100_items_is_accepted(client: TestClient[Litestar], db_session: Session) -> None:  # noqa: F811
    key = _issue_key(db_session)
    catalogue = _catalogue(db_session)

    response = _post(client, key, *[_item(catalogue, source_field=f"f{n}") for n in range(100)])

    assert response.json()["mentions_created"] == 100


def test_route_requires_the_machine_api_key(client: TestClient[Litestar], db_session: Session) -> None:  # noqa: F811
    catalogue = _catalogue(db_session)

    response = client.post(MENTIONS_URL, json={"items": [_item(catalogue)]})

    assert response.status_code == 401


LLM_FIELDS: dict[str, object] = {
    "source_field": "llm",
    "role": "issued",
    "condition": "bei Zuzug aus dem Ausland",
    "is_optional": True,
    "category_codes": ["home-and-housing", "moving-house", "birth-and-parenthood"],
}


@pytest.fixture
def vocabulary(db_session: Session) -> None:
    seed_canonical_taxonomy(db_session)


def _only_mention(db_session: Session) -> DiscoveryCandidateMention:
    db_session.expire_all()
    return db_session.scalars(select(DiscoveryCandidateMention)).one()


def test_mention_items_store_condition_optional_flag_and_codes(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
    vocabulary: None,
) -> None:
    key = _issue_key(db_session)
    catalogue = _catalogue(db_session)

    response = _post(client, key, _item(catalogue, **LLM_FIELDS))

    assert response.status_code == 200
    mention = _only_mention(db_session)
    assert mention.role is DiscoveryMentionRole.ISSUED
    assert (mention.condition, mention.is_optional) == ("bei Zuzug aus dem Ausland", True)
    assert mention.category_codes == ["home-and-housing", "moving-house", "birth-and-parenthood"]


def test_unknown_codes_are_dropped_and_counted_and_valid_codes_are_kept(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
    vocabulary: None,
) -> None:
    key = _issue_key(db_session)
    catalogue = _catalogue(db_session)
    item = _item(catalogue, source_field="llm", category_codes=["home-and-housing", "stale-code"])

    response = _post(client, key, item, _item(catalogue, source_field="llm2", category_codes=["stale-code"]))

    assert response.status_code == 200
    assert response.json()["unknown_codes"] == 2
    assert _count(db_session, DiscoveryCandidateMention) == 2
    stored = {m.source_field: m for m in db_session.scalars(select(DiscoveryCandidateMention))}
    assert stored["llm"].category_codes == ["home-and-housing"]
    assert stored["llm2"].category_codes == []


def test_a_reposted_llm_mention_updates_in_place_instead_of_adding_a_row(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
    vocabulary: None,
) -> None:
    key = _issue_key(db_session)
    catalogue = _catalogue(db_session)
    _post(client, key, _item(catalogue, **LLM_FIELDS))

    replay = _post(
        client,
        key,
        _item(catalogue, **{**LLM_FIELDS, "condition": None, "category_codes": ["moving-house", "birth-and-parenthood"]}),
    )

    assert replay.json()["mentions_updated"] == 1
    mention = _only_mention(db_session)
    assert (mention.condition, mention.category_codes) == (None, ["moving-house", "birth-and-parenthood"])


def test_items_without_the_new_fields_behave_exactly_as_before(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    key = _issue_key(db_session)
    catalogue = _catalogue(db_session)

    response = _post(client, key, _item(catalogue))

    assert response.json() == {
        "candidates_created": 1,
        "mentions_created": 1,
        "mentions_updated": 0,
        "unknown_codes": 0,
    }
    mention = _only_mention(db_session)
    assert (mention.condition, mention.is_optional, mention.category_codes) == (
        None,
        None,
        None,
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"category_codes": ["a", "b", "c", "d", "e", "f"]},
        {"category_codes": ["moving-house", "birth-and-parenthood", "renting-home", "a", "b", "c"]},
        {"condition": "x" * 301},
    ],
    ids=["six-categories", "six-categories-with-known-values", "long-condition"],
)
def test_too_many_codes_or_a_long_condition_is_a_422_and_writes_nothing(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
    overrides: dict[str, object],
) -> None:
    key = _issue_key(db_session)
    catalogue = _catalogue(db_session)

    response = _post(client, key, _item(catalogue, **overrides))

    assert response.status_code == 422
    assert _count(db_session, DiscoveryCandidateMention) == 0


@pytest.mark.parametrize(
    "overrides",
    [
        {"category_codes": ["home-and-housing", "moving-house"]},
        {"category_codes": ["moving-house", "birth-and-parenthood", "renting-home"]},
        {"condition": "x" * 300},
    ],
    ids=["two-categories", "three-categories", "300-condition"],
)
def test_codes_and_condition_at_their_limits_are_accepted(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
    overrides: dict[str, object],
) -> None:
    key = _issue_key(db_session)
    catalogue = _catalogue(db_session)

    assert _post(client, key, _item(catalogue, **overrides)).status_code == 200


PVOG_FIELDS: dict[str, object] = {
    "source_field": "details[code=pvog]",
    "role": "required",
    "category_codes": ["home-and-housing", "moving-house"],
    "direct_category_confidence": 0.95,
    "pvog_leaf_code": "1050100",
}


def test_mention_items_store_direct_confidence_and_leaf_code(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
    vocabulary: None,
) -> None:
    """situation-tag-hierarchy chapter 3: a PVOG mention's direct confidence and leaf code round-trip
    onto the stored mention, the two mention columns chapter 1 defines but left unpopulated."""
    key = _issue_key(db_session)
    catalogue = _catalogue(db_session)

    response = _post(client, key, _item(catalogue, **PVOG_FIELDS))

    assert response.status_code == 200
    mention = _only_mention(db_session)
    assert mention.direct_category_confidence == 0.95
    assert mention.pvog_leaf_code == "1050100"


def test_mention_items_without_direct_confidence_or_leaf_code_stay_null(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
) -> None:
    """An LLM-extracted mention (no PVOG fields at all) behaves exactly as before this chapter."""
    key = _issue_key(db_session)
    catalogue = _catalogue(db_session)

    response = _post(client, key, _item(catalogue))

    assert response.status_code == 200
    mention = _only_mention(db_session)
    assert (mention.direct_category_confidence, mention.pvog_leaf_code) == (
        None,
        None,
    )


def test_a_reposted_pvog_mention_updates_its_direct_confidence_and_leaf_code_in_place(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
    vocabulary: None,
) -> None:
    key = _issue_key(db_session)
    catalogue = _catalogue(db_session)
    _post(client, key, _item(catalogue, **PVOG_FIELDS))

    replay = _post(client, key, _item(catalogue, **{**PVOG_FIELDS, "direct_category_confidence": 0.65}))

    assert replay.json()["mentions_updated"] == 1
    mention = _only_mention(db_session)
    assert mention.direct_category_confidence == 0.65


def test_a_manual_mention_keeps_only_the_active_categories_it_names(
    client: TestClient[Litestar],  # noqa: F811
    db_session: Session,
    vocabulary: None,
) -> None:
    key = _issue_key(db_session)
    catalogue = _catalogue(db_session)
    item = _item(catalogue, extractor="manual", source_field="curated", category_codes=["moving-house", "retired-code"])

    response = _post(client, key, item)

    assert response.status_code == 200
    assert response.json()["unknown_codes"] == 1
    assert _only_mention(db_session).category_codes == ["moving-house"]
