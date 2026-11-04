"""Public, read-only candidate list and detail (chapter 3): no credentials, ranked by completeness."""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import app.features.discovery.dependencies as discovery_dependencies
import pytest
from app.config import settings
from app.features.discovery.budget_resources import BudgetResource
from app.features.discovery.budgets import BudgetService
from app.features.discovery.repository import DiscoveryRepository
from app.features.discovery.tags import MIN_SUGGESTED_SCORE
from app.main import create_app
from app.models.discovery import DiscoveryArtifactKind, DiscoveryCandidateStatus, DiscoveryMentionRole
from app.shared.object_store import InMemoryObjectStore, MeteredObjectStore, ObjectStore, ObjectStoreMeter, noop_meter
from litestar import Litestar
from litestar.testing import TestClient
from scripts.seed_taxonomy import seed_taxonomy
from sqlalchemy.orm import Session

from candidates_public_world import HOUSING, MOVING, Scene

URL = "/api/v1/candidates"
INTERNALS = {"extractor", "extractor_version", "artifact_id", "catalogue_service_id"}


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    """A client with no auth patches and no token: the routes under test must be public."""
    seed_taxonomy(db_session)
    monkeypatch.setattr("app.main.provide_session", lambda: db_session)
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def scene(db_session: Session) -> Scene:
    return Scene(db_session)


class CountingStore(InMemoryObjectStore):
    """An in-memory store that counts the reads that reach it."""

    def __init__(self) -> None:
        super().__init__()
        self.reads = 0

    def get(self, key: str) -> bytes:
        self.reads += 1
        return super().get(key)


class StoreSlot:
    """The store the app resolves for its ``object_store`` dependency; tests may swap or clear it."""

    def __init__(self) -> None:
        self.store: ObjectStore | None = CountingStore()

    @property
    def memory(self) -> CountingStore:
        assert isinstance(self.store, CountingStore)
        return self.store


@pytest.fixture
def slot(monkeypatch: pytest.MonkeyPatch) -> StoreSlot:
    """Put the slot's store under the ledger meter the discovery dependencies pass to ``get_object_store``."""
    holder = StoreSlot()

    def metered_slot_store(meter: ObjectStoreMeter = noop_meter) -> ObjectStore | None:
        return None if holder.store is None else MeteredObjectStore(holder.store, meter)

    monkeypatch.setattr(discovery_dependencies, "get_object_store", metered_slot_store)
    return holder


def _keys(response) -> list[str]:
    return [item["key"] for item in response.json()["items"]]


def _walk_keys(value: object) -> Iterator[str]:
    """Yield every JSON object key at any depth."""
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def test_candidates_list_is_public_and_ranks_by_completeness(client: TestClient[Litestar], scene: Scene) -> None:
    scene.candidate("bare")
    scene.complete_candidate("complete")

    response = client.get(URL)

    assert response.status_code == 200
    assert _keys(response) == ["complete", "complete-needs", "bare"]
    assert response.json()["total"] == 3


def test_candidates_list_shows_staged_and_emitted_candidates(client: TestClient[Litestar], scene: Scene) -> None:
    scene.candidate("staged-one")
    scene.candidate("emitted-one", status=DiscoveryCandidateStatus.EMITTED)

    statuses = {item["key"]: item["status"] for item in client.get(URL).json()["items"]}

    assert statuses == {"staged-one": "staged", "emitted-one": "emitted"}


def test_candidates_list_filters_by_complete(client: TestClient[Litestar], scene: Scene) -> None:
    scene.complete_candidate("complete")
    scene.candidate("bare")

    yes = client.get(URL, params={"filter[complete]": "yes"}).json()
    no = client.get(URL, params={"filter[complete]": "no"}).json()

    assert (_keys_of(yes), yes["total"]) == (["complete"], 1)
    assert "complete" not in _keys_of(no)
    assert "bare" in _keys_of(no)
    assert no["total"] == len(no["items"])


def _keys_of(body: dict) -> list[str]:
    return [item["key"] for item in body["items"]]


def test_candidates_list_filters_by_the_presence_of_a_domain_and_situation(
    client: TestClient[Litestar], scene: Scene
) -> None:
    scene.complete_candidate("accepted")
    lonely = scene.candidate("one-procedure-only")
    scene.mention(lonely, scene.procedure(), domains=[HOUSING], situations=[MOVING])

    domain = client.get(URL, params={"filter[domain]": HOUSING}).json()
    situation = client.get(URL, params={"filter[situation]": MOVING}).json()

    # document-browse-confidence chapter 2: a chip matches by the presence of the code, whatever its score,
    # so the one-procedure mention matches on either axis; tests/test_candidates_browse.py pins the sub-floor case.
    assert (set(_keys_of(domain)), domain["total"]) == ({"accepted", "one-procedure-only"}, 2)
    assert (set(_keys_of(situation)), situation["total"]) == ({"accepted", "one-procedure-only"}, 2)


def test_candidates_category_filter_returns_canonical_tags_and_confidence(
    client: TestClient[Litestar], scene: Scene
) -> None:
    owner = scene.candidate("canonical-tags")
    scene.mention(owner, scene.procedure(), domains=[HOUSING], situations=[MOVING])

    response = client.get(URL, params={"filter[category]": "home-and-housing"})

    assert response.status_code == 200
    [item] = response.json()["items"]
    assert [(tag["code"], tag["confidence"]) for tag in item["categories"]] == [
        ("home-and-housing", 0.5),
        ("moving-house", 0.5),
    ]


def test_candidates_unknown_category_filter_returns_422(
    client: TestClient[Litestar],
) -> None:
    response = client.get(URL, params={"filter[category]": "not-a-category"})

    assert response.status_code == 422
    assert "filter[category]" in str(response.json())


def test_candidates_conflicting_legacy_mapping_returns_diagnostic_422(
    client: TestClient[Litestar],
) -> None:
    response = client.get(
        URL,
        params={"filter[group]": "family-relationships", "filter[situation]": "moving-house"},
    )

    assert response.status_code == 422
    assert "conflicting legacy taxonomy filters" in str(response.json()).lower()


@pytest.mark.parametrize("param", ["filter[domain]", "filter[situation]", "filter[complete]", "filter[nope]"])
def test_candidates_list_rejects_an_unknown_filter_value(client: TestClient[Litestar], param: str) -> None:
    response = client.get(URL, params={param: "nope"})

    assert response.status_code == 422
    assert param in str(response.json())


@pytest.mark.parametrize(
    ("params", "status"),
    [
        ({"sort_by": "secret"}, 422),
        ({"sort_order": "desc"}, 422),
        ({"limit": 101}, 422),
        ({"limit": 0}, 422),
        ({"q": "x" * 201}, 422),
    ],
)
def test_candidates_list_rejects_an_unknown_sort_key_and_a_bad_limit(
    client: TestClient[Litestar], params: dict[str, object], status: int
) -> None:
    assert client.get(URL, params=params).status_code == status


def test_candidates_list_searches_titles_in_any_locale(client: TestClient[Litestar], scene: Scene) -> None:
    scene.candidate("german", title={"de": "Aufenthaltsbescheid"})
    scene.candidate("english", title={"en": "Registration certificate"})
    scene.candidate("percent", title={"de": "Anteil 50% Rabatt"})
    scene.candidate("number", title={"de": "Anteil 500 Rabatt"})

    german = client.get(URL, params={"q": "BESCHEID"}).json()
    english = client.get(URL, params={"q": "registration"}).json()
    literal = client.get(URL, params={"q": "50%"}).json()

    assert _keys_of(german) == ["german"]
    assert _keys_of(english) == ["english"]
    assert (_keys_of(literal), literal["total"]) == (["percent"], 1)


def test_candidates_list_pages_deterministically(client: TestClient[Litestar], scene: Scene) -> None:
    for key in ("c-doc", "a-doc", "b-doc"):
        scene.candidate(key)

    pages = [_keys(client.get(URL, params={"limit": 1, "offset": offset})) for offset in range(3)]

    assert pages == [["a-doc"], ["b-doc"], ["c-doc"]]


def test_candidate_card_resolves_the_title_for_the_requested_locale(client: TestClient[Litestar], scene: Scene) -> None:
    scene.candidate("both", title={"de": "Bescheid", "en": "Notice"})
    scene.candidate("german-only", title={"de": "Nachweis"})

    titles = {item["key"]: item["title"] for item in client.get(URL, headers={"Accept-Language": "en"}).json()["items"]}

    assert titles == {"both": "Notice", "german-only": "Nachweis"}


def test_candidate_description_is_the_best_mention_excerpt(client: TestClient[Litestar], scene: Scene) -> None:
    owner, bare = scene.candidate("subject"), scene.candidate("bare")
    issued, form, required = (scene.procedure(title) for title in ("Ausgestellt", "Formular", "Pflicht"))
    scene.mention(owner, issued, role=DiscoveryMentionRole.ISSUED, excerpt="issued excerpt", days_old=9)
    scene.mention(owner, form, role=DiscoveryMentionRole.FORM, excerpt="form excerpt", days_old=5)
    scene.mention(owner, required, excerpt="r" * 400, days_old=1)

    items = {item["key"]: item for item in client.get(URL).json()["items"]}

    assert items["subject"]["description"] == "r" * 300
    assert items["subject"]["description_source"] == "Pflicht"
    assert (items[bare.key]["description"], items[bare.key]["description_source"]) == (None, None)


def test_candidate_detail_splits_ingress_and_egress_by_edge_direction(
    client: TestClient[Litestar], scene: Scene
) -> None:
    needs, needed = scene.candidate("a-needs-b"), scene.candidate("b-needed")
    scene.edge(needs, needed, condition="nur bei Neuantrag", is_optional=True, excerpt="Der Antrag braucht B")

    parent = client.get(f"{URL}/{needs.id}").json()
    required = client.get(f"{URL}/{needed.id}").json()

    assert [n["id"] for n in parent["ingress"]] == [str(needed.id)] and parent["egress"] == []
    assert [n["id"] for n in required["egress"]] == [str(needs.id)] and required["ingress"] == []
    [neighbour] = parent["ingress"]
    assert (neighbour["condition"], neighbour["is_optional"]) == ("nur bei Neuantrag", True)
    assert (neighbour["excerpt"], neighbour["basis"]) == ("Der Antrag braucht B", "explicit")


def test_candidate_detail_merges_duplicate_edges_per_neighbour(client: TestClient[Litestar], scene: Scene) -> None:
    parent, required = scene.candidate("parent"), scene.candidate("required")
    older, newer = scene.procedure("Aeltere Leistung"), scene.procedure("Neuere Leistung")
    scene.edge(parent, required, older, condition="alt", is_optional=True, excerpt="alter Beleg", days_old=4)
    scene.edge(parent, required, newer, condition="neu", is_optional=False, excerpt="neuer Beleg", days_old=1)

    [merged] = client.get(f"{URL}/{parent.id}").json()["ingress"]

    assert merged["is_optional"] is False
    assert (merged["condition"], merged["excerpt"], merged["procedure_title"]) == (
        "alt",
        "alter Beleg",
        "Aeltere Leistung",
    )


def test_candidate_detail_caps_the_neighbours_per_side(client: TestClient[Litestar], scene: Scene) -> None:
    parent = scene.candidate("parent")
    for index in range(52):
        scene.edge(parent, scene.candidate(f"needed-{index:02d}"))

    body = client.get(f"{URL}/{parent.id}").json()

    assert (len(body["ingress"]), body["ingress_truncated"], body["egress_truncated"]) == (50, True, False)


def test_candidate_detail_hides_a_non_http_portal_url(client: TestClient[Litestar], scene: Scene) -> None:
    owner = scene.candidate("subject")
    urls = ["javascript:alert(1)", "data:text/html,x", "https://example.gov/leistung"]
    for index, url in enumerate(urls):
        scene.mention(owner, scene.procedure(f"Leistung {index}", portal_url=url), days_old=len(urls) - index)

    sources = client.get(f"{URL}/{owner.id}").json()["sources"]

    assert [source["portal_url"] for source in sources] == [None, None, "https://example.gov/leistung"]
    assert sources[0]["procedure_title"] == "Leistung 0"


def test_candidate_detail_returns_404_for_an_unknown_id(client: TestClient[Litestar]) -> None:
    unknown = client.get(f"{URL}/{uuid.uuid4()}")
    malformed = client.get(f"{URL}/not-a-uuid")

    assert unknown.status_code == 404
    assert "candidate not found" in unknown.json()["detail"].lower()
    assert malformed.status_code == 404


def test_candidate_detail_never_exposes_mention_internals(client: TestClient[Litestar], scene: Scene) -> None:
    scene.complete_candidate("subject")

    listing = client.get(URL).json()
    [item] = [item for item in listing["items"] if item["key"] == "subject"]
    detail = client.get(f"{URL}/{item['id']}").json()

    assert detail["sources"] and detail["ingress"]
    assert INTERNALS.isdisjoint(_walk_keys(listing))
    assert INTERNALS.isdisjoint(_walk_keys(detail))


def test_detail_screenshot_field_is_a_relative_proxy_path(client: TestClient[Litestar], scene: Scene) -> None:
    shot, none = scene.candidate("with-shot"), scene.candidate("without-shot")
    procedure = scene.procedure()
    scene.mention(shot, procedure)
    scene.artifact(procedure, DiscoveryArtifactKind.SCREENSHOT)

    present = client.get(f"{URL}/{shot.id}").json()
    absent = client.get(f"{URL}/{none.id}").json()

    assert present["screenshot"]["url"] == f"{URL}/{shot.id}/screenshot"
    assert present["screenshot"]["fetched_at"]
    assert absent["screenshot"] is None
    assert "X-Amz" not in str(present) and "memory://" not in str(present)


def _guards_by_path(prefix: str) -> dict[str, list[object]]:
    """Resolve the guards of every handler under ``prefix`` (app, router, controller and handler level)."""
    routes = [route for route in create_app().routes if route.path.startswith(prefix)]
    return {
        f"{route.path} {method}": list(handler.resolve_guards())
        for route in routes
        for method, (handler, _) in route.route_handler_map.items()
    }


def test_public_routes_have_no_auth_guards() -> None:
    public = _guards_by_path(URL)
    admin = _guards_by_path("/api/v1/discovery/admin/candidates")

    assert len(public) >= 2
    assert all(not guards for guards in public.values())
    assert admin and all(guards for guards in admin.values())


SHOT = "/screenshot"
IMMUTABLE = "public, max-age=31536000, immutable"


def _etag(data: bytes) -> str:
    return f'"{hashlib.sha256(data).hexdigest()}"'


def _class_b_reads(db_session: Session) -> float:
    """How many R2 Class B reads the budget ledger has counted in the current period."""
    status = BudgetService(DiscoveryRepository(db_session)).status(BudgetResource.R2_CLASS_B, datetime.now(UTC))
    return float(status.used)


def _with_shots(scene: Scene, slot: StoreSlot) -> uuid.UUID:
    """A candidate on two procedures with an older and a newer screenshot; return its id."""
    owner, old, new = scene.candidate("subject"), scene.procedure(), scene.procedure()
    scene.mention(owner, old)
    scene.mention(owner, new)
    scene.stored_screenshot(old, slot.memory, b"old-image", days_old=5)
    scene.stored_screenshot(new, slot.memory, b"new-image", days_old=1)
    return owner.id


def test_screenshot_streams_the_newest_image_with_immutable_headers(
    client: TestClient[Litestar], scene: Scene, slot: StoreSlot, db_session: Session
) -> None:
    candidate_id = _with_shots(scene, slot)

    response = client.get(f"{URL}/{candidate_id}{SHOT}")

    assert response.status_code == 200
    assert response.content == b"new-image"
    assert response.headers["content-type"].startswith("image/jpeg")
    assert response.headers["cache-control"] == IMMUTABLE
    assert response.headers["etag"] == _etag(b"new-image")
    assert _class_b_reads(db_session) == 1


def test_screenshot_answers_304_for_a_matching_etag_without_reading_the_store(
    client: TestClient[Litestar], scene: Scene, slot: StoreSlot, db_session: Session
) -> None:
    candidate_id = _with_shots(scene, slot)

    response = client.get(f"{URL}/{candidate_id}{SHOT}", headers={"If-None-Match": _etag(b"new-image")})

    assert response.status_code == 304
    assert response.content == b""
    assert (response.headers["etag"], response.headers["cache-control"]) == (_etag(b"new-image"), IMMUTABLE)
    assert slot.memory.reads == 0
    assert _class_b_reads(db_session) == 0


@pytest.mark.parametrize(
    ("header", "status"),
    [
        ("*", 304),
        ('W/"{sha}"', 304),
        ('"other", "{sha}"', 304),
        ('"other"', 200),
        ("", 200),
    ],
)
def test_screenshot_reads_every_form_of_if_none_match(
    client: TestClient[Litestar], scene: Scene, slot: StoreSlot, header: str, status: int
) -> None:
    candidate_id = _with_shots(scene, slot)
    sha = hashlib.sha256(b"new-image").hexdigest()

    response = client.get(f"{URL}/{candidate_id}{SHOT}", headers={"If-None-Match": header.format(sha=sha)})

    assert response.status_code == status


def test_screenshot_sends_the_image_for_a_stale_etag(
    client: TestClient[Litestar], scene: Scene, slot: StoreSlot
) -> None:
    candidate_id = _with_shots(scene, slot)

    stale = client.get(f"{URL}/{candidate_id}{SHOT}", headers={"If-None-Match": _etag(b"old-image")})

    assert (stale.status_code, stale.content) == (200, b"new-image")


def test_screenshot_is_404_without_an_image(client: TestClient[Litestar], scene: Scene, slot: StoreSlot) -> None:
    bare, elsewhere = scene.candidate("bare"), scene.candidate("elsewhere")
    scene.mention(elsewhere, scene.procedure())
    scene.stored_screenshot(scene.procedure(), slot.memory, b"not-theirs")

    no_image = client.get(f"{URL}/{bare.id}{SHOT}")
    other_procedure = client.get(f"{URL}/{elsewhere.id}{SHOT}")
    unknown = client.get(f"{URL}/{uuid.uuid4()}{SHOT}")

    assert (no_image.status_code, other_procedure.status_code, unknown.status_code) == (404, 404, 404)
    assert "no screenshot" in no_image.json()["detail"].lower()
    assert "candidate not found" in unknown.json()["detail"].lower()
    assert slot.memory.reads == 0


def test_screenshot_is_404_when_the_stored_object_is_gone(
    client: TestClient[Litestar], scene: Scene, slot: StoreSlot
) -> None:
    candidate_id = _with_shots(scene, slot)
    for key in slot.memory.stored_keys():
        slot.memory.delete(key)

    response = client.get(f"{URL}/{candidate_id}{SHOT}")

    assert response.status_code == 404
    assert "no screenshot" in response.json()["detail"].lower()


def test_screenshot_is_503_over_the_read_budget(
    client: TestClient[Litestar],
    scene: Scene,
    slot: StoreSlot,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate_id = _with_shots(scene, slot)
    monkeypatch.setattr(settings, "budget_r2_class_b_monthly", 0)

    response = client.get(f"{URL}/{candidate_id}{SHOT}")

    assert response.status_code == 503
    assert b"new-image" not in response.content
    assert slot.memory.reads == 0
    assert _class_b_reads(db_session) == 0


def test_screenshot_is_503_when_storage_is_not_configured(
    client: TestClient[Litestar], scene: Scene, slot: StoreSlot
) -> None:
    candidate_id = _with_shots(scene, slot)
    slot.store = None

    response = client.get(f"{URL}/{candidate_id}{SHOT}")

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"].lower()


def _tags(body: dict, key: str, axis: str) -> list[tuple[str, float]]:
    item = next(item for item in body["items"] if item["key"] == key)
    return [(tag["code"], round(tag["confidence"], 6)) for tag in item[axis]]


def test_candidate_card_lists_every_tag_with_its_confidence_most_confident_first(
    client: TestClient[Litestar], scene: Scene
) -> None:
    owner = scene.candidate("tagged")
    first, second = scene.procedure(), scene.procedure()
    for procedure in (first, second):
        scene.mention(owner, procedure, domains=[HOUSING], situations=[MOVING])
    scene.mention(owner, first, domains=["work"])

    body = client.get(URL).json()

    assert _tags(body, "tagged", "domains") == [(HOUSING, 0.85), ("work", 0.25)]
    assert _tags(body, "tagged", "situations") == [(MOVING, 0.85)]


def test_candidate_card_keeps_a_tag_below_the_old_inclusion_floor(client: TestClient[Litestar], scene: Scene) -> None:
    owner = scene.candidate("weak")
    procedures = [scene.procedure() for _ in range(12)]
    scene.mention(owner, procedures[0], domains=["rare"])
    for procedure in procedures[1:]:
        scene.mention(owner, procedure, domains=[HOUSING])

    tags = dict(_tags(client.get(URL).json(), "weak", "domains"))

    assert 0 < tags["rare"] < MIN_SUGGESTED_SCORE
    assert tags[HOUSING] > tags["rare"]


def test_candidate_card_without_mentions_lists_no_tags(client: TestClient[Litestar], scene: Scene) -> None:
    scene.candidate("untagged")

    body = client.get(URL).json()

    assert (_tags(body, "untagged", "domains"), _tags(body, "untagged", "situations")) == ([], [])
