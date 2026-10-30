"""Characterize discovery persistence behaviour so the repository split stays behaviour-preserving."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from app.features.discovery.catalogue_upsert import CatalogueUpsertService
from app.features.discovery.claim_service import ClaimDraft, ClaimService
from app.features.discovery.errors import UnknownJurisdictionError
from app.features.discovery.repository import DiscoveryRepository, FetchLogEntry, TaskTarget
from app.models.discovery import (
    LEGACY_TASK_KINDS,
    CatalogueService,
    DiscoveryClaim,
    DiscoveryClaimKind,
    DiscoverySource,
    DiscoveryTask,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.schema.discovery.machine import CatalogueBatchItem
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

PAYLOAD = {"title_i18n": {"de": "Ausweis"}, "official_url": "https://example.gov/doc"}


@pytest.fixture
def repo(db_session: Session) -> DiscoveryRepository:
    return DiscoveryRepository(db_session)


@pytest.fixture
def upserts(repo: DiscoveryRepository) -> CatalogueUpsertService:
    return CatalogueUpsertService(repo)


@pytest.fixture
def claims(repo: DiscoveryRepository) -> ClaimService:
    return ClaimService(repo)


@pytest.fixture
def country(db_session: Session) -> Jurisdiction:
    row = Jurisdiction(kind=JurisdictionKind.COUNTRY, name_i18n={"en": "T"}, code=f"C{uuid.uuid4().hex[:8]}")
    db_session.add(row)
    db_session.flush()
    return row


def _item(jurisdiction_id: uuid.UUID, *, external_id: str = "svc-1", title: str = "Alt") -> CatalogueBatchItem:
    return CatalogueBatchItem(
        source=DiscoverySource.FIM,
        external_id=external_id,
        jurisdiction_id=jurisdiction_id,
        title_i18n={"de": title},
        portal_url="https://example.gov/portal",
    )


def _catalogue(repo: DiscoveryRepository, country: Jurisdiction, external_id: str = "svc-1") -> CatalogueService:
    row, _ = CatalogueUpsertService(repo).upsert(_item(country.id, external_id=external_id))
    return row


def _target(cat: CatalogueService) -> TaskTarget:
    return TaskTarget(catalogue_service_id=cat.id, kind=DiscoveryTaskKind.FETCH_URL, target_url="https://x/a")


def _count(session: Session, model: type) -> int:
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


def test_catalogue_upsert_creates_then_updates_in_place(
    repo: DiscoveryRepository, upserts: CatalogueUpsertService, country: Jurisdiction
) -> None:
    first, created = upserts.upsert(_item(country.id))
    second, created_again = upserts.upsert(_item(country.id, title="Neu"))
    assert (created, created_again) == (True, False)
    assert second.id == first.id
    assert second.title_i18n == {"de": "Neu"}
    assert first.pipeline_stage == "T0"
    found = repo.get_catalogue_by_source_external_id(source=DiscoverySource.FIM, external_id="svc-1")
    assert found is not None and found.id == first.id


def test_catalogue_upsert_unknown_jurisdiction_raises_without_write(
    repo: DiscoveryRepository, upserts: CatalogueUpsertService, db_session: Session
) -> None:
    with pytest.raises(UnknownJurisdictionError):
        upserts.upsert(_item(uuid.uuid4()))
    assert _count(db_session, CatalogueService) == 0
    assert repo.get_catalogue_by_source_external_id(source=DiscoverySource.FIM, external_id="svc-1") is None


def test_task_insert_is_found_by_target_and_status(repo: DiscoveryRepository, country: Jurisdiction) -> None:
    cat = _catalogue(repo, country)
    task = repo.insert_task(_target(cat))
    assert repo.find_task_for_target(_target(cat), statuses=(DiscoveryTaskStatus.PENDING,)) == task
    assert repo.list_pending_tasks_for_claim(limit=10, kinds=LEGACY_TASK_KINDS, now=datetime.now(UTC)) == [task]
    assert repo.get_task(task.id) == task


def test_task_lookup_ignores_other_status_and_unknown_id(repo: DiscoveryRepository, country: Jurisdiction) -> None:
    cat = _catalogue(repo, country)
    repo.insert_task(_target(cat))
    assert repo.find_task_for_target(_target(cat), statuses=(DiscoveryTaskStatus.FAILED,)) is None
    assert repo.get_task(uuid.uuid4()) is None


def test_reclaim_expired_claims_returns_task_to_pending(
    repo: DiscoveryRepository, country: Jurisdiction, db_session: Session
) -> None:
    cat = _catalogue(repo, country)
    task = repo.insert_task(_target(cat))
    now = datetime.now(UTC)
    task.status = DiscoveryTaskStatus.CLAIMED
    task.lease_expires_at = now - timedelta(minutes=1)
    repo.reclaim_expired_claims(now=now, max_attempts=3)
    db_session.refresh(task)
    assert task.status == DiscoveryTaskStatus.PENDING
    assert task.lease_expires_at is None


def test_reclaim_expired_claims_keeps_live_lease(
    repo: DiscoveryRepository, country: Jurisdiction, db_session: Session
) -> None:
    cat = _catalogue(repo, country)
    task = repo.insert_task(_target(cat))
    now = datetime.now(UTC)
    task.status = DiscoveryTaskStatus.CLAIMED
    task.lease_expires_at = now + timedelta(minutes=5)
    repo.reclaim_expired_claims(now=now, max_attempts=3)
    db_session.refresh(task)
    assert task.status == DiscoveryTaskStatus.CLAIMED


def test_entity_upsert_dedupes_on_canonical_url(repo: DiscoveryRepository, country: Jurisdiction) -> None:
    cat = _catalogue(repo, country)
    first, created = repo.upsert_entity(catalogue_service_id=cat.id, canonical_url="https://e.gov/a", label=None)
    again, created_again = repo.upsert_entity(catalogue_service_id=cat.id, canonical_url="https://e.gov/a", label="L")
    assert (created, created_again) == (True, False)
    assert again.id == first.id and again.label == "L"
    assert repo.get_entity(first.id) == first


def test_entity_lookup_unknown_id_returns_none(repo: DiscoveryRepository) -> None:
    assert repo.get_entity(uuid.uuid4()) is None


def _entity_id(repo: DiscoveryRepository, country: Jurisdiction) -> uuid.UUID:
    cat = _catalogue(repo, country)
    return repo.upsert_entity(catalogue_service_id=cat.id, canonical_url="https://e.gov/a", label=None)[0].id


def _append(claims: ClaimService, entity_id: uuid.UUID, confidence: str) -> tuple[DiscoveryClaim, bool]:
    draft = ClaimDraft(
        discovery_entity_id=entity_id,
        kind=DiscoveryClaimKind.NEW_DOCUMENT,
        payload=PAYLOAD,
        confidence=Decimal(confidence),
    )
    return claims.append_claim(draft)


def test_claim_append_creates_row(
    repo: DiscoveryRepository, claims: ClaimService, country: Jurisdiction, db_session: Session
) -> None:
    row, created = _append(claims, _entity_id(repo, country), "0.5")
    assert created is True
    assert row.payload_fingerprint
    assert _count(db_session, DiscoveryClaim) == 1


def test_claim_append_same_fingerprint_is_idempotent(
    repo: DiscoveryRepository, claims: ClaimService, country: Jurisdiction, db_session: Session
) -> None:
    entity_id = _entity_id(repo, country)
    first, _ = _append(claims, entity_id, "0.5")
    second, created = _append(claims, entity_id, "0.9")
    assert created is False and second.id == first.id
    assert second.confidence == Decimal("0.9")
    assert _count(db_session, DiscoveryClaim) == 1


def test_claim_append_lost_race_recovers_without_extra_row(
    repo: DiscoveryRepository, claims: ClaimService, country: Jurisdiction, db_session: Session
) -> None:
    entity_id = _entity_id(repo, country)
    first, _ = _append(claims, entity_id, "0.5")
    db_session.commit()
    original_find = repo.find_claim_by_fingerprint
    calls = 0

    def racing_find(**kwargs: object) -> DiscoveryClaim | None:
        nonlocal calls
        calls += 1
        return None if calls == 1 else original_find(**kwargs)  # type: ignore[arg-type]

    with patch.object(repo, "find_claim_by_fingerprint", racing_find):
        row, created = _append(claims, entity_id, "0.7")
    assert created is False and row.id == first.id
    assert row.confidence == Decimal("0.7")
    assert _count(db_session, DiscoveryClaim) == 1


def test_claim_append_integrity_error_without_winner_propagates(
    repo: DiscoveryRepository, claims: ClaimService, country: Jurisdiction, db_session: Session
) -> None:
    entity_id = _entity_id(repo, country)
    with (
        patch.object(repo, "find_claim_by_fingerprint", lambda **_: None),
        patch.object(db_session, "flush", side_effect=IntegrityError("i", {}, Exception("boom"))),
        pytest.raises(IntegrityError),
    ):
        _append(claims, entity_id, "0.5")


def test_fetch_log_append_links_task(repo: DiscoveryRepository, country: Jurisdiction) -> None:
    cat = _catalogue(repo, country)
    task = repo.insert_task(_target(cat))
    row = repo.append_fetch_log(
        FetchLogEntry(
            discovery_task_id=task.id,
            http_status=200,
            content_type="text/html",
            byte_length=10,
            error_message=None,
            fetched_at=datetime.now(UTC),
        )
    )
    assert row.discovery_task_id == task.id
    assert repo.list_catalogue_fetch_logs(cat.id) == [row]


def test_coverage_metrics_count_sources_tasks_and_t4(repo: DiscoveryRepository, country: Jurisdiction) -> None:
    cat = _catalogue(repo, country)
    cat.pipeline_stage = "T4"
    repo.insert_task(_target(cat))
    metrics = repo.fetch_coverage_metrics()
    assert metrics.by_source == {"fim": 1}
    assert (metrics.task_counts.pending, metrics.task_counts.failed, metrics.emit_ready_count) == (1, 0, 1)


def test_coverage_metrics_empty_database_is_all_zero(repo: DiscoveryRepository) -> None:
    metrics = repo.fetch_coverage_metrics()
    assert (metrics.by_source, metrics.task_counts.total, metrics.emit_ready_count) == ({}, 0, 0)


def test_catalogue_summary_groups_by_source_and_stage(
    repo: DiscoveryRepository, country: Jurisdiction, db_session: Session
) -> None:
    _catalogue(repo, country)
    total, by_source, by_stage = repo.catalogue_summary()
    assert (total, by_source, by_stage) == (1, {"fim": 1}, {"T0": 1})
    assert _count(db_session, DiscoveryTask) == 0
