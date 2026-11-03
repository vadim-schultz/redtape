"""Pin catalogue stage derivation and the statement cost of advance_stage on the write path."""

from __future__ import annotations

import re
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

import pytest
from app.db import engine as db_engine
from app.features.discovery.catalogue_upsert import CatalogueUpsertService
from app.features.discovery.claim_service import ClaimDraft, ClaimService
from app.features.discovery.pipeline import PipelineStage
from app.features.discovery.repository import DiscoveryRepository, FetchLogEntry, TaskTarget
from app.features.discovery.service import DiscoveryMachineService
from app.features.discovery.stage_sync import advance_stage, derive_stage_for
from app.models.discovery import (
    CatalogueService,
    DiscoveryClaimKind,
    DiscoverySource,
    DiscoveryTaskKind,
)
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.schema.discovery.machine import (
    CatalogueBatchItem,
    CatalogueBatchRequest,
    ClaimAppendRequest,
    FetchLogAppendRequest,
)
from sqlalchemy import event
from sqlalchemy.orm import Session

PORTAL = "https://example.gov/portal"
PAYLOAD = {"title_i18n": {"de": "Ausweis"}, "official_url": "https://example.gov/doc"}
_CLAIM_PAYLOAD_COLUMN = re.compile(r"discovery_claim\.payload\b")
Recorded = list[tuple[str, int]]


@pytest.fixture
def repo(db_session: Session) -> DiscoveryRepository:
    return DiscoveryRepository(db_session)


@pytest.fixture
def country(db_session: Session) -> Jurisdiction:
    row = Jurisdiction(kind=JurisdictionKind.COUNTRY, name_i18n={"en": "T"}, code=f"C{uuid.uuid4().hex[:8]}")
    db_session.add(row)
    db_session.flush()
    return row


def _catalogue(
    repo: DiscoveryRepository,
    country: Jurisdiction,
    *,
    portal_url: str | None = PORTAL,
    external_id: str = "svc-1",
) -> CatalogueService:
    item = CatalogueBatchItem(
        source=DiscoverySource.FIM,
        external_id=external_id,
        jurisdiction_id=country.id,
        title_i18n={"de": "Alt"},
        portal_url=portal_url,
    )
    row, _ = CatalogueUpsertService(repo).upsert(item)
    return row


def _task(repo: DiscoveryRepository, cat: CatalogueService) -> uuid.UUID:
    target = TaskTarget(catalogue_service_id=cat.id, kind=DiscoveryTaskKind.FETCH_URL, target_url=PORTAL)
    return repo.insert_task(target).id


def _fetch_log(repo: DiscoveryRepository, task_id: uuid.UUID) -> None:
    entry = FetchLogEntry(
        discovery_task_id=task_id,
        http_status=200,
        content_type="text/html",
        byte_length=10,
        error_message=None,
        fetched_at=datetime.now(UTC),
    )
    repo.append_fetch_log(entry)


def _entity_id(repo: DiscoveryRepository, cat: CatalogueService) -> uuid.UUID:
    return repo.upsert_entity(catalogue_service_id=cat.id, canonical_url="https://e.gov/a", label=None)[0].id


def _claim(
    repo: DiscoveryRepository,
    entity_id: uuid.UUID,
    kind: DiscoveryClaimKind,
    payload: dict[str, object],
) -> None:
    draft = ClaimDraft(discovery_entity_id=entity_id, kind=kind, payload=payload, confidence=None)
    ClaimService(repo).append_claim(draft)


def _stored_stage(db_session: Session, catalogue_id: uuid.UUID) -> str:
    row = db_session.get(CatalogueService, catalogue_id)
    assert row is not None
    return row.pipeline_stage


@contextmanager
def _recorded_statements() -> Iterator[Recorded]:
    """Yield a list that collects ``(statement, rowcount)`` for every cursor execute on the engine."""
    seen: Recorded = []

    def record(_conn: object, cursor: object, statement: str, *_args: object) -> None:
        seen.append((statement, int(getattr(cursor, "rowcount", 0))))

    event.listen(db_engine, "after_cursor_execute", record)
    try:
        yield seen
    finally:
        event.remove(db_engine, "after_cursor_execute", record)


def _selects(seen: Recorded) -> list[str]:
    return [text for text, _ in seen if text.lstrip().upper().startswith("SELECT")]


def _claim_rows_read(seen: Recorded) -> int:
    return sum(
        rows for text, rows in seen if text.lstrip().upper().startswith("SELECT") and _CLAIM_PAYLOAD_COLUMN.search(text)
    )


# Characterisation: stage derivation on the unchanged code.


def test_derive_stage_for_returns_T0_for_a_bare_catalogue_row(repo: DiscoveryRepository, country: Jurisdiction) -> None:
    cat = _catalogue(repo, country)
    assert derive_stage_for(repo, cat.id) is PipelineStage.T0


def test_derive_stage_for_returns_T1_with_a_task(repo: DiscoveryRepository, country: Jurisdiction) -> None:
    cat = _catalogue(repo, country)
    _task(repo, cat)
    assert derive_stage_for(repo, cat.id) is PipelineStage.T1


def test_derive_stage_for_returns_T2_with_a_fetch_log(repo: DiscoveryRepository, country: Jurisdiction) -> None:
    cat = _catalogue(repo, country)
    _fetch_log(repo, _task(repo, cat))
    assert derive_stage_for(repo, cat.id) is PipelineStage.T2


def test_derive_stage_for_returns_T3_with_an_unresolvable_claim(
    repo: DiscoveryRepository, country: Jurisdiction
) -> None:
    cat = _catalogue(repo, country)
    _claim(repo, _entity_id(repo, cat), DiscoveryClaimKind.NEW_DOCUMENT, {"title_i18n": {"de": "x"}})
    assert derive_stage_for(repo, cat.id) is PipelineStage.T3


def test_derive_stage_for_returns_T4_with_only_resolvable_emit_claims(
    repo: DiscoveryRepository, country: Jurisdiction
) -> None:
    cat = _catalogue(repo, country)
    _claim(repo, _entity_id(repo, cat), DiscoveryClaimKind.NEW_DOCUMENT, PAYLOAD)
    assert derive_stage_for(repo, cat.id) is PipelineStage.T4


def test_metadata_only_claims_stay_T3(repo: DiscoveryRepository, country: Jurisdiction) -> None:
    cat = _catalogue(repo, country)
    _claim(repo, _entity_id(repo, cat), DiscoveryClaimKind.METADATA, {"kurztext": "Kurz"})
    assert derive_stage_for(repo, cat.id) is PipelineStage.T3


def test_new_document_claim_without_official_url_is_not_resolvable(
    repo: DiscoveryRepository, country: Jurisdiction
) -> None:
    cat = _catalogue(repo, country)
    entity_id = _entity_id(repo, cat)
    _claim(repo, entity_id, DiscoveryClaimKind.NEW_DOCUMENT, {"title_i18n": {"de": "x"}})
    _claim(repo, entity_id, DiscoveryClaimKind.NEW_DOCUMENT, {"official_url": "https://example.gov/x"})
    assert derive_stage_for(repo, cat.id) is PipelineStage.T3


def test_derive_stage_for_unknown_catalogue_id_is_T0(repo: DiscoveryRepository) -> None:
    assert derive_stage_for(repo, uuid.uuid4()) is PipelineStage.T0


def test_advance_stage_raises_but_never_lowers(
    repo: DiscoveryRepository, country: Jurisdiction, db_session: Session
) -> None:
    done = _catalogue(repo, country, external_id="done")
    done.pipeline_stage = "T4"
    advance_stage(repo, done)
    assert done.pipeline_stage == "T4"

    fresh = _catalogue(repo, country, external_id="fresh")
    _task(repo, fresh)
    advance_stage(repo, fresh)
    assert fresh.pipeline_stage == "T1"


def test_batch_upsert_advances_stage_to_T1_for_item_with_portal_url(
    repo: DiscoveryRepository, country: Jurisdiction, db_session: Session
) -> None:
    item = CatalogueBatchItem(
        source=DiscoverySource.FIM,
        external_id="svc-1",
        jurisdiction_id=country.id,
        title_i18n={"de": "Alt"},
        portal_url=PORTAL,
    )
    DiscoveryMachineService(repo).batch_upsert(CatalogueBatchRequest(items=[item]))
    row = db_session.query(CatalogueService).filter_by(external_id="svc-1").one()
    assert row.pipeline_stage == "T1"


def test_batch_upsert_without_portal_url_stays_T0(
    repo: DiscoveryRepository, country: Jurisdiction, db_session: Session
) -> None:
    item = CatalogueBatchItem(
        source=DiscoverySource.FIM,
        external_id="svc-1",
        jurisdiction_id=country.id,
        title_i18n={"de": "Alt"},
        portal_url=None,
    )
    DiscoveryMachineService(repo).batch_upsert(CatalogueBatchRequest(items=[item]))
    row = db_session.query(CatalogueService).filter_by(external_id="svc-1").one()
    assert row.pipeline_stage == "T0"


def test_append_fetch_log_advances_to_T2(repo: DiscoveryRepository, country: Jurisdiction, db_session: Session) -> None:
    cat = _catalogue(repo, country)
    task_id = _task(repo, cat)
    DiscoveryMachineService(repo).append_fetch_log(task_id, FetchLogAppendRequest(http_status=200))
    assert _stored_stage(db_session, cat.id) == "T2"


def test_append_claim_advances_to_T3_then_T4(
    repo: DiscoveryRepository, country: Jurisdiction, db_session: Session
) -> None:
    cat = _catalogue(repo, country)
    entity_id = _entity_id(repo, cat)
    service = DiscoveryMachineService(repo)
    service.append_claim(ClaimAppendRequest(discovery_entity_id=entity_id, kind=DiscoveryClaimKind.METADATA))
    assert _stored_stage(db_session, cat.id) == "T3"
    service.append_claim(
        ClaimAppendRequest(discovery_entity_id=entity_id, kind=DiscoveryClaimKind.NEW_DOCUMENT, payload=PAYLOAD)
    )
    assert _stored_stage(db_session, cat.id) == "T4"


def test_enqueue_for_service_returns_task_when_task_already_exists(
    repo: DiscoveryRepository, country: Jurisdiction
) -> None:
    cat = _catalogue(repo, country)
    first = DiscoveryMachineService(repo)._queue.enqueue_for_service(cat)
    second = DiscoveryMachineService(repo)._queue.enqueue_for_service(cat)
    assert first is not None
    assert second is not None
    assert second.id == first.id


# Characterisation: the three repository additions.


def test_catalogue_has_tasks_true_and_false(repo: DiscoveryRepository, country: Jurisdiction) -> None:
    cat = _catalogue(repo, country)
    other = _catalogue(repo, country, external_id="svc-2")
    _task(repo, cat)
    assert repo.catalogue_has_tasks(cat.id) is True
    assert repo.catalogue_has_tasks(other.id) is False


def test_catalogue_has_fetch_log_true_and_false(repo: DiscoveryRepository, country: Jurisdiction) -> None:
    cat = _catalogue(repo, country)
    other = _catalogue(repo, country, external_id="svc-2")
    _fetch_log(repo, _task(repo, cat))
    assert repo.catalogue_has_fetch_log(cat.id) is True
    assert repo.catalogue_has_fetch_log(other.id) is False


def test_claim_projection_returns_kind_and_payload_only(repo: DiscoveryRepository, country: Jurisdiction) -> None:
    cat = _catalogue(repo, country)
    _claim(repo, _entity_id(repo, cat), DiscoveryClaimKind.NEW_DOCUMENT, PAYLOAD)
    rows = repo.catalogue_claim_kinds_and_payloads(cat.id)
    assert rows == [(DiscoveryClaimKind.NEW_DOCUMENT, PAYLOAD)]


# Red: statement and row cost of the write path.


def test_advance_stage_issues_at_most_three_selects(repo: DiscoveryRepository, country: Jurisdiction) -> None:
    cat = _catalogue(repo, country)
    _fetch_log(repo, _task(repo, cat))
    _claim(repo, _entity_id(repo, cat), DiscoveryClaimKind.METADATA, {"kurztext": "Kurz"})
    with _recorded_statements() as seen:
        advance_stage(repo, cat)
    selects = _selects(seen)
    assert len(selects) <= 3
    assert any("EXISTS" in text.upper() for text in selects)
    claim_selects = [text for text in selects if "discovery_claim" in text]
    assert claim_selects
    assert all("discovery_claim.id" not in text and "discovery_claim.created_at" not in text for text in claim_selects)


def test_appending_n_claims_reads_constant_rows_per_append(
    repo: DiscoveryRepository, country: Jurisdiction, db_session: Session
) -> None:
    cat = _catalogue(repo, country)
    entity_id = _entity_id(repo, cat)
    service = DiscoveryMachineService(repo)
    claim_rows: list[int] = []
    statement_counts: list[int] = []
    for i in range(20):
        payload = {"title_i18n": {"de": f"Ausweis {i}"}, "official_url": f"https://example.gov/doc-{i}"}
        with _recorded_statements() as seen:
            service.append_claim(
                ClaimAppendRequest(discovery_entity_id=entity_id, kind=DiscoveryClaimKind.NEW_DOCUMENT, payload=payload)
            )
        claim_rows.append(_claim_rows_read(seen))
        statement_counts.append(len(seen))
    assert _stored_stage(db_session, cat.id) == "T4"
    assert len(set(statement_counts[1:])) == 1
    assert len(set(claim_rows[1:])) == 1
    assert claim_rows[-1] <= claim_rows[0]


def test_advance_stage_issues_no_stage_queries_once_T4(repo: DiscoveryRepository, country: Jurisdiction) -> None:
    cat = _catalogue(repo, country)
    _claim(repo, _entity_id(repo, cat), DiscoveryClaimKind.NEW_DOCUMENT, PAYLOAD)
    cat.pipeline_stage = "T4"
    with _recorded_statements() as seen:
        advance_stage(repo, cat)
    assert _selects(seen) == []
