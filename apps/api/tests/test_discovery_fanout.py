"""Catalogue upsert fanout rules and batch integration (chapter 14)."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import app.features.auth.guard_session as guard_session_module
import app.features.discovery.fanout as fanout_module
import pytest
from app.config import settings
from app.features.auth.repository import ApiKeyRepository
from app.features.auth.service import ApiKeyService
from app.features.discovery.fanout import apply_fanout_for_service, fanout_specs_for_service
from app.features.discovery.repository import DiscoveryRepository
from app.features.discovery.steckbrief_key import steckbrief_key
from app.main import create_app
from app.models.discovery import (
    CatalogueService,
    DiscoveryEvent,
    DiscoveryEventType,
    DiscoverySource,
    DiscoveryTask,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from litestar import Litestar
from litestar.testing import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

BATCH_URL = "/api/v1/discovery/machine/catalogue/batch"
FIM_STECKBRIEF_KEY = "01234567890123"
STECKBRIEF_URL = "https://fimportal.de/api/v1/leistung-steckbriefe/{key}"
KEY_CASES: list[dict[str, object]] = json.loads(
    (Path(__file__).parent / "fixtures" / "steckbrief_key_cases.json").read_text(encoding="utf-8")
)["cases"]


@contextmanager
def _keep_open(session: Session) -> Iterator[Session]:
    yield session


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient[Litestar]]:
    monkeypatch.setattr(settings, "discovery_machine_opt_in", True)
    monkeypatch.setattr(guard_session_module, "SessionLocal", lambda: _keep_open(db_session))
    monkeypatch.setattr("app.main.provide_session", lambda: db_session)
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def country(db_session: Session) -> Jurisdiction:
    jurisdiction = Jurisdiction(
        kind=JurisdictionKind.COUNTRY,
        name_i18n={"en": "Testland"},
        code=f"T{uuid.uuid4().hex[:8]}",
    )
    db_session.add(jurisdiction)
    db_session.flush()
    return jurisdiction


def _govdata_service(
    db_session: Session,
    country: Jurisdiction,
    *,
    raw_payload: dict[str, object],
    external_id: str = "govdata:ozg:fanout-test",
) -> CatalogueService:
    row = CatalogueService(
        source=DiscoverySource.GOVDATA,
        external_id=external_id,
        jurisdiction_id=country.id,
        title_i18n={"de": "Leistung"},
        portal_url="https://example.gov/service",
        raw_payload=raw_payload,
        pipeline_stage="T0",
    )
    db_session.add(row)
    db_session.flush()
    return row


def _issue_key(db_session: Session) -> str:
    service = ApiKeyService(ApiKeyRepository(db_session))
    key = service.issue("discovery-ingest")
    service.verify(key)
    db_session.flush()
    return key


def _batch_item(country: Jurisdiction, **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "source": "govdata",
        "external_id": "govdata:ozg:fanout-http",
        "jurisdiction_id": str(country.id),
        "title_i18n": {"de": "Leistung"},
        "portal_url": "https://example.gov/service",
        "raw_payload": {"ozgid": "fanout-http", "fim_id": FIM_STECKBRIEF_KEY},
    }
    body.update(overrides)
    return body


def test_fanout_enqueues_enrich_metadata_when_raw_payload_contains_fim_id(
    db_session: Session,
    country: Jurisdiction,
) -> None:
    """fanout · enqueues enrich_metadata when raw_payload contains fim_id."""
    service = _govdata_service(db_session, country, raw_payload={"fim_id": FIM_STECKBRIEF_KEY})
    repo = DiscoveryRepository(db_session)

    specs = fanout_specs_for_service(service)
    assert len(specs) == 1
    assert specs[0].kind == DiscoveryTaskKind.ENRICH_METADATA
    assert specs[0].target_url.endswith(FIM_STECKBRIEF_KEY)
    assert specs[0].priority > 100

    tasks = apply_fanout_for_service(repo, service)
    assert len(tasks) == 1
    assert tasks[0].kind == DiscoveryTaskKind.ENRICH_METADATA
    assert tasks[0].status == DiscoveryTaskStatus.PENDING

    events = list(
        db_session.scalars(
            select(DiscoveryEvent).where(
                DiscoveryEvent.catalogue_service_id == service.id,
                DiscoveryEvent.event_type == DiscoveryEventType.TASK_ENQUEUED,
            )
        )
    )
    assert len(events) == 1
    assert events[0].payload["kind"] == "enrich_metadata"


def test_fanout_does_not_duplicate_pending_enrich_task_on_re_upsert(
    db_session: Session,
    country: Jurisdiction,
) -> None:
    """fanout · does not duplicate pending enrich task on re-upsert."""
    service = _govdata_service(db_session, country, raw_payload={"fim_id": FIM_STECKBRIEF_KEY})
    repo = DiscoveryRepository(db_session)

    first = apply_fanout_for_service(repo, service)
    second = apply_fanout_for_service(repo, service)

    assert len(first) == 1
    assert second == []

    pending = list(
        db_session.scalars(
            select(DiscoveryTask).where(
                DiscoveryTask.catalogue_service_id == service.id,
                DiscoveryTask.kind == DiscoveryTaskKind.ENRICH_METADATA,
                DiscoveryTask.status == DiscoveryTaskStatus.PENDING,
            )
        )
    )
    assert len(pending) == 1


def test_fanout_skips_enrich_when_fim_id_missing(db_session: Session, country: Jurisdiction) -> None:
    """fanout · skips enrich when fim_id missing."""
    service = _govdata_service(db_session, country, raw_payload={"ozgid": "no-fim"})
    repo = DiscoveryRepository(db_session)

    assert fanout_specs_for_service(service) == []
    assert apply_fanout_for_service(repo, service) == []


def test_batch_upsert_integration_creates_fetch_and_enrich_tasks(
    client: TestClient[Litestar],
    db_session: Session,
    country: Jurisdiction,
) -> None:
    """batch upsert integration · creates fetch and enrich tasks."""
    key = _issue_key(db_session)
    response = client.post(
        BATCH_URL,
        json={"items": [_batch_item(country)]},
        headers={"X-API-Key": key},
    )

    assert response.status_code == 201
    catalogue_id = uuid.UUID(response.json()["items"][0]["id"])

    tasks = list(
        db_session.scalars(
            select(DiscoveryTask)
            .where(DiscoveryTask.catalogue_service_id == catalogue_id)
            .order_by(DiscoveryTask.priority.asc())
        )
    )
    assert len(tasks) == 2
    kinds = {task.kind for task in tasks}
    assert kinds == {DiscoveryTaskKind.FETCH_URL, DiscoveryTaskKind.ENRICH_METADATA}
    enrich = next(task for task in tasks if task.kind == DiscoveryTaskKind.ENRICH_METADATA)
    assert FIM_STECKBRIEF_KEY in enrich.target_url
    assert enrich.priority > next(task for task in tasks if task.kind == DiscoveryTaskKind.FETCH_URL).priority


PVOG_PORTAL_URL = "https://pvog.example.de/leistung/1"
PVOG_DETAILS: list[dict[str, object]] = [{"code": "08", "title": "Erforderliche Unterlagen", "filled": True}]


def _pvog_service(
    db_session: Session,
    country: Jurisdiction,
    *,
    raw_payload: dict[str, object],
    portal_url: str | None = PVOG_PORTAL_URL,
) -> CatalogueService:
    row = CatalogueService(
        source=DiscoverySource.PVOG,
        external_id="pvog:leika:99001040001000",
        jurisdiction_id=country.id,
        title_i18n={"de": "Leistung"},
        portal_url=portal_url,
        raw_payload=raw_payload,
        pipeline_stage="T0",
    )
    db_session.add(row)
    db_session.flush()
    return row


def _harvest_tasks(db_session: Session, service: CatalogueService) -> list[DiscoveryTask]:
    return list(
        db_session.scalars(
            select(DiscoveryTask)
            .where(
                DiscoveryTask.catalogue_service_id == service.id,
                DiscoveryTask.kind == DiscoveryTaskKind.HARVEST_PAYLOAD,
            )
            .order_by(DiscoveryTask.created_at.asc())
        )
    )


def test_pvog_row_with_details_enqueues_a_harvest_task_with_a_versioned_input_key(
    db_session: Session,
    country: Jurisdiction,
) -> None:
    """pvog row with details · enqueues a harvest task with a versioned input key."""
    service = _pvog_service(db_session, country, raw_payload={"details": PVOG_DETAILS})

    specs = fanout_specs_for_service(service)
    assert [(s.kind, s.target_url, s.priority, s.input_key) for s in specs] == [
        (DiscoveryTaskKind.HARVEST_PAYLOAD, PVOG_PORTAL_URL, 50, f"pvog-payload@{fanout_module.PVOG_HARVESTER_VERSION}")
    ]

    tasks = apply_fanout_for_service(DiscoveryRepository(db_session), service)
    assert [(t.kind, t.status, t.input_key) for t in tasks] == [
        (DiscoveryTaskKind.HARVEST_PAYLOAD, DiscoveryTaskStatus.PENDING, specs[0].input_key)
    ]


def test_pvog_row_without_a_portal_url_still_gets_a_harvest_task_keyed_by_its_external_id(
    db_session: Session,
    country: Jurisdiction,
) -> None:
    """pvog row without a portal url · still gets a harvest task keyed by its external id."""
    service = _pvog_service(db_session, country, raw_payload={"details": PVOG_DETAILS}, portal_url=None)

    specs = fanout_specs_for_service(service)

    assert [s.target_url for s in specs] == ["pvog-payload:pvog:leika:99001040001000"]


def test_govdata_row_and_pvog_row_without_details_enqueue_none(db_session: Session, country: Jurisdiction) -> None:
    """govdata row and pvog row without details · enqueue none."""
    govdata = _govdata_service(db_session, country, raw_payload={"details": PVOG_DETAILS})
    repo = DiscoveryRepository(db_session)

    assert fanout_specs_for_service(govdata) == []
    for payload in ({}, {"details": []}, {"details": "broken"}, {"details": None}):
        service = _pvog_service(db_session, country, raw_payload=payload)
        assert fanout_specs_for_service(service) == []
        assert apply_fanout_for_service(repo, service) == []
        db_session.delete(service)
        db_session.flush()


def test_re_fanout_is_idempotent_for_the_same_version_and_creates_a_task_for_a_new_version(
    db_session: Session,
    country: Jurisdiction,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """re-fanout · is idempotent for the same version and creates a task for a new version."""
    service = _pvog_service(db_session, country, raw_payload={"details": PVOG_DETAILS})
    repo = DiscoveryRepository(db_session)

    first = apply_fanout_for_service(repo, service)
    again = apply_fanout_for_service(repo, service)
    monkeypatch.setattr(fanout_module, "PVOG_HARVESTER_VERSION", "next")
    bumped = apply_fanout_for_service(repo, service)

    assert (len(first), again) == (1, [])
    assert [t.input_key for t in bumped] == ["pvog-payload@next"]
    assert len(_harvest_tasks(db_session, service)) == 2


def test_batch_upsert_of_a_pvog_row_creates_fetch_and_harvest_tasks(
    client: TestClient[Litestar],
    db_session: Session,
    country: Jurisdiction,
) -> None:
    """batch upsert · of a pvog row creates fetch and harvest tasks."""
    item = _batch_item(
        country,
        source="pvog",
        external_id="pvog:leika:99001040001000",
        portal_url=PVOG_PORTAL_URL,
        raw_payload={"details": PVOG_DETAILS},
    )
    response = client.post(BATCH_URL, json={"items": [item]}, headers={"X-API-Key": _issue_key(db_session)})

    assert response.status_code == 201
    tasks = list(
        db_session.scalars(
            select(DiscoveryTask).where(
                DiscoveryTask.catalogue_service_id == uuid.UUID(response.json()["items"][0]["id"])
            )
        )
    )
    assert {t.kind for t in tasks} == {DiscoveryTaskKind.FETCH_URL, DiscoveryTaskKind.HARVEST_PAYLOAD}
    harvest = next(t for t in tasks if t.kind == DiscoveryTaskKind.HARVEST_PAYLOAD)
    assert (harvest.priority, harvest.target_url) == (50, PVOG_PORTAL_URL)


@pytest.mark.parametrize("case", KEY_CASES, ids=[str(case["name"]) for case in KEY_CASES])
def test_steckbrief_key_follows_the_shared_case_table(case: dict[str, object]) -> None:
    """steckbrief key · follows the shared case table (also run by the ingest resolver)."""
    assert steckbrief_key(case["raw_payload"]) == case["key"]  # type: ignore[arg-type]


def test_govdata_row_with_a_leika_key_enqueues_an_enrich_task_for_that_steckbrief_url(
    db_session: Session,
    country: Jurisdiction,
) -> None:
    """govdata row with leika_key · enqueues an enrich task for that steckbrief url."""
    service = _govdata_service(db_session, country, raw_payload={"leika_key": "99096049001001"})

    specs = fanout_specs_for_service(service)

    assert [(s.kind, s.target_url, s.priority) for s in specs] == [
        (DiscoveryTaskKind.ENRICH_METADATA, STECKBRIEF_URL.format(key="99096049001001"), 200)
    ]
    tasks = apply_fanout_for_service(DiscoveryRepository(db_session), service)
    assert [(t.kind, t.target_url) for t in tasks] == [(DiscoveryTaskKind.ENRICH_METADATA, specs[0].target_url)]


def test_pvog_row_with_leikakeys_enqueues_an_enrich_task_for_the_first_key(
    db_session: Session,
    country: Jurisdiction,
) -> None:
    """pvog row with leikakeys · enqueues an enrich task for the first key."""
    payload = {"details": PVOG_DETAILS, "leikakeys": ["99155004000000", "99111011017000"]}
    service = _pvog_service(db_session, country, raw_payload=payload)

    specs = fanout_specs_for_service(service)

    enrich = [s for s in specs if s.kind == DiscoveryTaskKind.ENRICH_METADATA]
    assert [(s.target_url, s.priority, s.input_key) for s in enrich] == [
        (STECKBRIEF_URL.format(key="99155004000000"), 200, None)
    ]
    assert {s.kind for s in specs} == {DiscoveryTaskKind.ENRICH_METADATA, DiscoveryTaskKind.HARVEST_PAYLOAD}


def test_fim_id_takes_precedence_over_leika_key_in_the_enrich_task(db_session: Session, country: Jurisdiction) -> None:
    """fim_id · takes precedence over leika_key in the enrich task."""
    payload = {"fim_id": FIM_STECKBRIEF_KEY, "leika_key": "99096049001001"}
    service = _govdata_service(db_session, country, raw_payload=payload)

    assert [s.target_url for s in fanout_specs_for_service(service)] == [STECKBRIEF_URL.format(key=FIM_STECKBRIEF_KEY)]


@pytest.mark.parametrize(
    "payload",
    [{}, {"leika_key": "12345"}, {"leika_key": None}, {"leikakeys": []}, {"leikakeys": ["bad"]}, {"fim_id": 7}],
)
def test_malformed_or_missing_keys_enqueue_nothing(
    db_session: Session,
    country: Jurisdiction,
    payload: dict[str, object],
) -> None:
    """malformed or missing keys · enqueue nothing for govdata and pvog rows."""
    repo = DiscoveryRepository(db_session)
    govdata = _govdata_service(db_session, country, raw_payload=payload)
    pvog = _pvog_service(db_session, country, raw_payload=payload)

    for service in (govdata, pvog):
        assert fanout_specs_for_service(service) == []
        assert apply_fanout_for_service(repo, service) == []


def test_re_fanout_of_a_leika_key_row_is_idempotent(db_session: Session, country: Jurisdiction) -> None:
    """re-fanout · of a leika key row is idempotent."""
    service = _govdata_service(db_session, country, raw_payload={"leika_key": "99096049001001"})
    repo = DiscoveryRepository(db_session)

    first = apply_fanout_for_service(repo, service)
    again = apply_fanout_for_service(repo, service)

    assert (len(first), again) == (1, [])
