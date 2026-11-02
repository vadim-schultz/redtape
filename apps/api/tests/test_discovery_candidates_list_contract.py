"""Admin candidate list contract (chapter 4): a sort key and filter per table column, plus the completeness flags."""

from __future__ import annotations

import uuid

import pytest
from app.config import settings
from app.features.discovery.repository import DiscoveryRepository
from app.features.discovery.repository.candidate_completeness import completeness_subquery
from app.features.discovery.repository.candidate_listing import CandidateListingRepository
from app.models.discovery import DiscoveryArtifactKind, DiscoveryCandidateStatus, DiscoveryMentionRole
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from litestar import Litestar
from litestar.testing import TestClient
from scripts.seed_taxonomy import seed_taxonomy
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import Subquery

from candidates_public_world import HOUSING, MOVING, Scene
from test_discovery_admin_api import ADMIN_EMAIL, _admin_headers, _token
from test_discovery_machine_api import _issue_key

URL = "/api/v1/discovery/admin/candidates"
MACHINE_URL = "/api/v1/discovery/machine/candidates"
NEW_KEYS = ("jurisdiction", "status", "roles", "completeness")
FLAGS = ("has_domain", "has_situation", "has_edges", "has_snapshot", "has_screenshot")
Client = TestClient[Litestar]


@pytest.fixture
def scene(db_session: Session) -> Scene:
    return Scene(db_session)


@pytest.fixture
def taxonomy(db_session: Session) -> None:
    seed_taxonomy(db_session)


def _named(session: Session, name: str) -> Jurisdiction:
    row = Jurisdiction(kind=JurisdictionKind.COUNTRY, name_i18n={"de": name}, code=f"T{uuid.uuid4().hex[:8]}")
    session.add(row)
    session.flush()
    return row


def _in(session: Session, name: str) -> Scene:
    """Return a scene whose rows belong to a new jurisdiction called ``name``."""
    scene = Scene(session)
    scene.jurisdiction = _named(session, name)
    return scene


def _get(client: Client, **params: object) -> dict:
    response = client.get(URL, params=params, headers=_admin_headers())
    assert response.status_code == 200, response.text
    return response.json()


def _keys(client: Client, **params: object) -> list[str]:
    return [item["key"] for item in _get(client, **params)["items"]]


def _mixed(scene: Scene) -> None:
    """Candidates with every flag count, role set, status and a second jurisdiction."""
    scene.complete_candidate("full")
    snapshot_only = scene.candidate("snap-only")
    procedure = scene.procedure()
    scene.mention(snapshot_only, procedure, role=DiscoveryMentionRole.FORM)
    scene.artifact(procedure, DiscoveryArtifactKind.HTML_SNAPSHOT, content_type="text/html")
    scene.candidate("bare", status=DiscoveryCandidateStatus.EMITTED)
    _in(scene.session, "Aachen").candidate("elsewhere")


def test_candidate_list_sorts_by_jurisdiction_both_ways(client: Client, db_session: Session) -> None:
    bremen, berlin, aachen = (_in(db_session, name) for name in ("Bremen", "Berlin", "Aachen"))
    bremen.candidate("in-bremen")
    berlin.candidate("in-berlin-b")
    berlin.candidate("in-berlin-a")
    aachen.candidate("in-aachen")

    ascending = _keys(client, sort_by="jurisdiction", sort_order="asc")
    descending = _keys(client, sort_by="jurisdiction", sort_order="desc")

    assert ascending == ["in-aachen", "in-berlin-a", "in-berlin-b", "in-bremen"]
    assert descending == ["in-bremen", "in-berlin-a", "in-berlin-b", "in-aachen"]


def test_candidate_list_sorts_by_status(client: Client, scene: Scene) -> None:
    scene.candidate("a-emitted", status=DiscoveryCandidateStatus.EMITTED)
    scene.candidate("b-staged")
    scene.candidate("c-staged")

    assert _keys(client, sort_by="status", sort_order="asc") == ["b-staged", "c-staged", "a-emitted"]
    assert _keys(client, sort_by="status", sort_order="desc") == ["a-emitted", "b-staged", "c-staged"]


def test_candidate_list_sorts_by_roles(client: Client, scene: Scene) -> None:
    scene.candidate("none")
    procedure = scene.procedure()
    required, form, both = (scene.candidate(key) for key in ("only-required", "only-form", "both"))
    scene.mention(required, procedure, role=DiscoveryMentionRole.REQUIRED)
    scene.mention(form, procedure, role=DiscoveryMentionRole.FORM)
    scene.mention(both, procedure, role=DiscoveryMentionRole.REQUIRED)
    scene.mention(both, procedure, role=DiscoveryMentionRole.FORM)

    ascending = _keys(client, sort_by="roles", sort_order="asc")
    descending = _keys(client, sort_by="roles", sort_order="desc")

    assert ascending == ["none", "only-form", "only-required", "both"]
    assert descending == ["both", "only-required", "only-form", "none"]


def test_candidate_list_sorts_by_completeness(client: Client, scene: Scene) -> None:
    _mixed(scene)

    ascending = _keys(client, sort_by="completeness", sort_order="asc")
    descending = _keys(client, sort_by="completeness", sort_order="desc")

    assert ascending == ["bare", "elsewhere", "full-needs", "snap-only", "full"]
    assert descending == ["full", "full-needs", "snap-only", "bare", "elsewhere"]


@pytest.mark.parametrize("key", NEW_KEYS)
@pytest.mark.parametrize("order", ["asc", "desc"])
def test_candidate_list_pages_deterministically_on_every_new_key(
    client: Client, scene: Scene, key: str, order: str
) -> None:
    _mixed(scene)
    whole = _keys(client, sort_by=key, sort_order=order)

    paged = [_keys(client, sort_by=key, sort_order=order, limit=1, offset=offset)[0] for offset in range(len(whole))]

    assert paged == whole and len(set(whole)) == len(whole) == 5


def test_candidate_list_filters_by_complete_and_each_flag(client: Client, scene: Scene) -> None:
    _mixed(scene)

    complete = _get(client, **{"filter[complete]": "yes", "limit": 1})
    incomplete = _keys(client, **{"filter[complete]": "no"})

    assert [item["key"] for item in complete["items"]] == ["full"] and complete["total"] == 1
    assert sorted(incomplete) == ["bare", "elsewhere", "full-needs", "snap-only"]
    assert _keys(client, **{"filter[has_screenshot]": "no", "sort_by": "title"}) == [
        "bare",
        "elsewhere",
        "full-needs",
        "snap-only",
    ]
    assert _keys(client, **{"filter[has_snapshot]": "yes", "sort_by": "title"}) == ["full", "snap-only"]
    assert _keys(client, **{"filter[has_edges]": "yes", "sort_by": "title"}) == ["full", "full-needs"]
    assert _get(client, **{"filter[has_domain]": "yes", "limit": 1})["total"] == 1
    assert _get(client, **{"filter[has_situation]": "no", "limit": 1})["total"] == 4


def test_candidate_list_filters_by_jurisdiction(client: Client, db_session: Session) -> None:
    aachen, berlin = _in(db_session, "Aachen"), _in(db_session, "Berlin")
    aachen.candidate("in-aachen")
    berlin.candidate("in-berlin")

    matched = _get(client, **{"filter[jurisdiction]": str(aachen.jurisdiction.id)})
    unknown = _get(client, **{"filter[jurisdiction]": str(uuid.uuid4())})

    assert [item["key"] for item in matched["items"]] == ["in-aachen"] and matched["total"] == 1
    assert unknown["items"] == [] and unknown["total"] == 0


def test_candidate_list_rejects_a_jurisdiction_that_is_not_a_uuid(client: Client, scene: Scene) -> None:
    scene.candidate("anything")

    response = client.get(URL, params={"filter[jurisdiction]": "berlin"}, headers=_admin_headers())

    assert response.status_code == 422
    assert [e["key"] for e in response.json()["extra"]] == ["filter[jurisdiction]"]


@pytest.mark.usefixtures("taxonomy")
def test_candidate_list_filters_by_an_accepted_domain_code(client: Client, scene: Scene) -> None:
    scene.complete_candidate("accepted")
    lonely = scene.candidate("lonely")
    scene.mention(lonely, scene.procedure(), domains=[HOUSING], situations=[MOVING])

    domain = _keys(client, **{"filter[domain]": HOUSING})
    situation = _keys(client, **{"filter[situation]": MOVING})
    other = _get(client, **{"filter[domain]": "identity-civil-status"})

    # situation-tag-hierarchy chapter 1: both axes now run the same scoring engine (D8), so "lonely"'s
    # single mention clears the inclusion floor on either axis, the same way.
    assert set(domain) == {"accepted", "lonely"}
    assert set(situation) == {"accepted", "lonely"}
    assert other["items"] == []


@pytest.mark.usefixtures("taxonomy")
@pytest.mark.parametrize("key", ["filter[domain]", "filter[situation]"])
def test_candidate_list_rejects_an_unknown_taxonomy_code(client: Client, scene: Scene, key: str) -> None:
    scene.complete_candidate("accepted")

    response = client.get(URL, params={key: "no-such-code"}, headers=_admin_headers())

    assert response.status_code == 422
    assert [e["key"] for e in response.json()["extra"]] == [key]


@pytest.mark.parametrize("key", ["filter[complete]", *(f"filter[{flag}]" for flag in FLAGS)])
def test_candidate_list_rejects_an_invalid_flag_value(client: Client, scene: Scene, key: str) -> None:
    scene.candidate("anything")

    response = client.get(URL, params={key: "maybe"}, headers=_admin_headers())

    assert response.status_code == 422
    assert [(e["key"], e["source"]) for e in response.json()["extra"]] == [(key, "query")]


def test_candidate_list_joins_the_completeness_model_only_when_it_is_needed(
    client: Client, scene: Scene, monkeypatch: pytest.MonkeyPatch
) -> None:
    scene.candidate("anything")
    joined: list[str] = []

    def spy() -> Subquery:
        joined.append("joined")
        return completeness_subquery()

    monkeypatch.setattr("app.features.discovery.repository.candidate_relations.completeness_subquery", spy)

    plain = client.get(URL, params={"sort_by": "roles", "filter[status]": "staged"}, headers=_admin_headers())
    assert plain.status_code == 200 and joined == []
    for params in ({"sort_by": "completeness"}, {"filter[has_edges]": "no"}):
        assert client.get(URL, params=params, headers=_admin_headers()).status_code == 200
    assert joined == ["joined"] * 4


def test_candidate_list_rejects_an_unknown_sort_key_without_querying(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    queried: list[str] = []
    monkeypatch.setattr(CandidateListingRepository, "count_candidates", lambda *_: queried.append("count") or 0)
    monkeypatch.setattr(CandidateListingRepository, "list_candidates_page", lambda *_: queried.append("page") or [])

    response = client.get(URL, params={"sort_by": "roles2"}, headers=_admin_headers())

    assert response.status_code == 422
    assert [e["key"] for e in response.json()["extra"]] == ["sort_by"]
    assert queried == []


def test_legacy_parameters_still_work_and_canonical_ones_win(client: Client, scene: Scene) -> None:
    procedure = scene.procedure()
    busy, quiet = scene.candidate("busy"), scene.candidate("quiet")
    sent = scene.candidate("sent", status=DiscoveryCandidateStatus.EMITTED)
    for owner in (busy, busy, quiet, sent, sent):
        scene.mention(owner, procedure)

    legacy = _keys(client, status="staged", min_mentions=2, sort="mentions_desc")
    canonical = _keys(client, **{"filter[status]": "emitted", "status": "staged"})

    assert legacy == ["busy"]
    assert canonical == ["sent"]


def test_candidate_list_rows_carry_the_completeness_flags(client: Client, scene: Scene, db_session: Session) -> None:
    _mixed(scene)

    items = _get(client)["items"]
    expected = DiscoveryRepository(db_session).completeness_for([uuid.UUID(item["id"]) for item in items])

    for item in items:
        read = expected[uuid.UUID(item["id"])]
        assert item["completeness"] == read.completeness and item["complete"] is read.complete
        assert item["flags"] == {name: getattr(read, name) for name in FLAGS}
    assert {item["key"]: item["completeness"] for item in items}["full"] == 5


def test_candidate_list_stays_admin_only(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    stranger = {"Authorization": f"Bearer {_token(sub=uuid.uuid4(), email='stranger@example.com')}"}
    admin = {"Authorization": f"Bearer {_token(sub=uuid.uuid4(), email=ADMIN_EMAIL)}"}
    assert client.get(URL, params={"sort_by": "roles"}).status_code == 401
    assert client.get(URL, params={"sort_by": "roles"}, headers=stranger).status_code == 403

    monkeypatch.setattr(settings, "discovery_admin_emails", "")
    monkeypatch.setattr(settings, "discovery_machine_opt_in", False)

    assert client.get(URL, params={"sort_by": "roles"}, headers=admin).status_code == 503


def test_machine_candidate_list_is_unchanged(
    client: Client, scene: Scene, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "discovery_machine_opt_in", True)
    procedure = scene.procedure()
    busy, quiet = scene.candidate("busy"), scene.candidate("quiet")
    for owner in (busy, busy, quiet):
        scene.mention(owner, procedure)
    headers = {"X-API-Key": _issue_key(db_session)}

    both = client.get(MACHINE_URL, headers=headers).json()
    narrowed = client.get(MACHINE_URL, params={"status": "staged", "min_mentions": 2}, headers=headers).json()
    widened = client.get(MACHINE_URL, params={"filter[complete]": "yes", "sort_by": "roles"}, headers=headers)

    assert [item["key"] for item in narrowed["items"]] == ["busy"] and narrowed["total"] == 1
    assert widened.status_code == 200 and widened.json()["total"] == both["total"] == 2
    assert {"id", "key", "title_i18n", "status", "mention_count", "roles", "jurisdiction_name_i18n"} <= set(
        both["items"][0]
    )
