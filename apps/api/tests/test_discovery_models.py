"""Tests for discovery staging ORM models (chapter 1)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from app.models.discovery import (
    CatalogueService,
    DiscoveryArtifact,
    DiscoveryArtifactKind,
    DiscoveryBudgetLedger,
    DiscoveryCandidateEdge,
    DiscoveryCandidateMention,
    DiscoveryCandidateStatus,
    DiscoveryDocumentCandidate,
    DiscoveryEdgeBasis,
    DiscoveryEntity,
    DiscoveryEvent,
    DiscoveryEventType,
    DiscoveryMentionRole,
    DiscoverySource,
    DiscoveryTask,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def _jurisdiction(session: Session) -> Jurisdiction:
    country = Jurisdiction(
        kind=JurisdictionKind.COUNTRY,
        name_i18n={"en": "Testland"},
        code=f"T{uuid.uuid4().hex[:8]}",
    )
    session.add(country)
    session.flush()
    return country


def _catalogue_service(session: Session, *, external_id: str = "svc-1") -> CatalogueService:
    jurisdiction = _jurisdiction(session)
    row = CatalogueService(
        source=DiscoverySource.GOVDATA,
        external_id=external_id,
        jurisdiction_id=jurisdiction.id,
        title_i18n={"de": "Leistung"},
        raw_payload={"id": external_id},
        pipeline_stage="T0",
    )
    session.add(row)
    session.flush()
    return row


def test_catalogue_service_unique_source_external_id_rejects_duplicate(db_session: Session) -> None:
    first = _catalogue_service(db_session, external_id="dup-ext")
    duplicate = CatalogueService(
        source=first.source,
        external_id=first.external_id,
        jurisdiction_id=first.jurisdiction_id,
        title_i18n={"de": "Other"},
        raw_payload={},
        pipeline_stage="T0",
    )
    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_discovery_task_defaults_to_pending_status(db_session: Session) -> None:
    catalogue = _catalogue_service(db_session)
    task = DiscoveryTask(
        catalogue_service_id=catalogue.id,
        kind=DiscoveryTaskKind.FETCH_URL,
        target_url="https://example.gov/service",
    )
    db_session.add(task)
    db_session.flush()
    db_session.expire(task)

    assert task.status == DiscoveryTaskStatus.PENDING
    assert task.priority == 100


def test_discovery_entity_cascade_delete_when_catalogue_service_removed(db_session: Session) -> None:
    catalogue = _catalogue_service(db_session)
    entity = DiscoveryEntity(
        catalogue_service_id=catalogue.id,
        canonical_url="https://example.gov/form.pdf",
    )
    db_session.add(entity)
    db_session.flush()
    entity_id = entity.id

    db_session.delete(catalogue)
    db_session.flush()

    assert db_session.get(DiscoveryEntity, entity_id) is None


def test_discovery_event_records_event_type_and_optional_fks(db_session: Session) -> None:
    catalogue = _catalogue_service(db_session)
    task = DiscoveryTask(
        catalogue_service_id=catalogue.id,
        kind=DiscoveryTaskKind.FETCH_URL,
        target_url="https://example.gov/service",
    )
    db_session.add(task)
    db_session.flush()

    event = DiscoveryEvent(
        event_type=DiscoveryEventType.TASK_ENQUEUED,
        catalogue_service_id=catalogue.id,
        discovery_task_id=task.id,
        payload={"kind": "fetch_url"},
    )
    db_session.add(event)
    db_session.flush()
    db_session.expire(event)

    loaded = db_session.get(DiscoveryEvent, event.id)
    assert loaded is not None
    assert loaded.event_type == DiscoveryEventType.TASK_ENQUEUED
    assert loaded.catalogue_service_id == catalogue.id
    assert loaded.discovery_task_id == task.id
    assert loaded.payload == {"kind": "fetch_url"}


def test_pipeline_stage_check_rejects_t9(db_session: Session) -> None:
    jurisdiction = _jurisdiction(db_session)
    row = CatalogueService(
        source=DiscoverySource.MANUAL,
        external_id="bad-stage",
        jurisdiction_id=jurisdiction.id,
        title_i18n={"en": "x"},
        raw_payload={},
        pipeline_stage="T9",
    )
    db_session.add(row)

    with pytest.raises(IntegrityError):
        db_session.flush()


def _candidate(
    session: Session, jurisdiction_id: uuid.UUID, *, key: str = "personalausweis"
) -> DiscoveryDocumentCandidate:
    row = DiscoveryDocumentCandidate(jurisdiction_id=jurisdiction_id, key=key, title_i18n={"de": "Personalausweis"})
    session.add(row)
    session.flush()
    return row


def _mention(
    candidate: DiscoveryDocumentCandidate,
    catalogue: CatalogueService,
    *,
    role: DiscoveryMentionRole = DiscoveryMentionRole.REQUIRED,
    source_field: str = "details[0]",
) -> DiscoveryCandidateMention:
    return DiscoveryCandidateMention(
        candidate_id=candidate.id,
        catalogue_service_id=catalogue.id,
        role=role,
        excerpt="Bitte Personalausweis mitbringen",
        source_field=source_field,
        extractor="pvog_payload",
        extractor_version="1",
    )


def test_candidate_defaults_to_staged_without_suggestion(db_session: Session) -> None:
    catalogue = _catalogue_service(db_session)
    candidate = _candidate(db_session, catalogue.jurisdiction_id)
    db_session.expire(candidate)

    assert candidate.status == DiscoveryCandidateStatus.STAGED
    assert candidate.suggestion_id is None
    assert candidate.official_url is None


def test_candidate_unique_per_jurisdiction_and_key(db_session: Session) -> None:
    catalogue = _catalogue_service(db_session)
    _candidate(db_session, catalogue.jurisdiction_id)
    db_session.add(
        DiscoveryDocumentCandidate(
            jurisdiction_id=catalogue.jurisdiction_id, key="personalausweis", title_i18n={"en": "ID card"}
        )
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_candidate_key_may_repeat_across_jurisdictions(db_session: Session) -> None:
    first = _catalogue_service(db_session, external_id="svc-a")
    second = _catalogue_service(db_session, external_id="svc-b")

    _candidate(db_session, first.jurisdiction_id)
    _candidate(db_session, second.jurisdiction_id)


def test_mention_unique_per_candidate_service_role_and_field(db_session: Session) -> None:
    catalogue = _catalogue_service(db_session)
    candidate = _candidate(db_session, catalogue.jurisdiction_id)
    db_session.add(_mention(candidate, catalogue))
    db_session.flush()
    db_session.add(_mention(candidate, catalogue))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_mention_may_repeat_with_another_role(db_session: Session) -> None:
    catalogue = _catalogue_service(db_session)
    candidate = _candidate(db_session, catalogue.jurisdiction_id)
    db_session.add(_mention(candidate, catalogue))
    db_session.add(_mention(candidate, catalogue, role=DiscoveryMentionRole.FORM))

    db_session.flush()


def test_deleting_a_catalogue_row_cascades_its_mentions(db_session: Session) -> None:
    catalogue = _catalogue_service(db_session)
    candidate = _candidate(db_session, catalogue.jurisdiction_id)
    mention = _mention(candidate, catalogue)
    db_session.add(mention)
    db_session.flush()
    mention_id = mention.id

    db_session.delete(catalogue)
    db_session.flush()
    db_session.expire_all()

    assert db_session.get(DiscoveryCandidateMention, mention_id) is None
    assert db_session.get(DiscoveryDocumentCandidate, candidate.id) is not None


def test_deleting_a_candidate_cascades_its_mentions(db_session: Session) -> None:
    catalogue = _catalogue_service(db_session)
    candidate = _candidate(db_session, catalogue.jurisdiction_id)
    mention = _mention(candidate, catalogue)
    db_session.add(mention)
    db_session.flush()
    mention_id = mention.id

    db_session.delete(candidate)
    db_session.flush()
    db_session.expire_all()

    assert db_session.get(DiscoveryCandidateMention, mention_id) is None


def _artifact(
    session: Session,
    catalogue: CatalogueService,
    *,
    kind: DiscoveryArtifactKind = DiscoveryArtifactKind.HTML_SNAPSHOT,
    sha256: str = "a" * 64,
    task: DiscoveryTask | None = None,
) -> DiscoveryArtifact:
    artifact = DiscoveryArtifact(
        catalogue_service_id=catalogue.id,
        discovery_task_id=task.id if task is not None else None,
        kind=kind,
        storage_key=f"discovery/{catalogue.id}/{kind.value}/{sha256}.html",
        sha256=sha256,
        content_type="text/html",
        byte_size=12,
        source_url="https://example.gov/page",
        fetched_at=datetime.now(UTC),
    )
    session.add(artifact)
    session.flush()
    return artifact


def _task(session: Session, catalogue: CatalogueService) -> DiscoveryTask:
    task = DiscoveryTask(
        catalogue_service_id=catalogue.id, kind=DiscoveryTaskKind.FETCH_URL, target_url="https://example.gov/page"
    )
    session.add(task)
    session.flush()
    return task


def test_artifact_unique_per_catalogue_kind_and_sha256(db_session: Session) -> None:
    catalogue = _catalogue_service(db_session)
    other = _catalogue_service(db_session, external_id="svc-2")
    _artifact(db_session, catalogue)

    _artifact(db_session, catalogue, kind=DiscoveryArtifactKind.SCREENSHOT)
    _artifact(db_session, other)
    with pytest.raises(IntegrityError):
        _artifact(db_session, catalogue)


def test_deleting_a_catalogue_row_cascades_its_artifacts(db_session: Session) -> None:
    catalogue = _catalogue_service(db_session)
    artifact_id = _artifact(db_session, catalogue).id

    db_session.delete(catalogue)
    db_session.flush()
    db_session.expire_all()

    assert db_session.get(DiscoveryArtifact, artifact_id) is None


def test_deleting_a_task_nulls_the_artifact_reference_and_keeps_the_artifact(db_session: Session) -> None:
    catalogue = _catalogue_service(db_session)
    task = _task(db_session, catalogue)
    artifact = _artifact(db_session, catalogue, task=task)

    db_session.delete(task)
    db_session.flush()
    db_session.refresh(artifact)

    assert artifact.discovery_task_id is None


def test_deleting_an_artifact_nulls_the_task_and_mention_references(db_session: Session) -> None:
    catalogue = _catalogue_service(db_session)
    task = _task(db_session, catalogue)
    artifact = _artifact(db_session, catalogue)
    task.artifact_id = artifact.id
    candidate = DiscoveryDocumentCandidate(
        jurisdiction_id=catalogue.jurisdiction_id, key="pass", title_i18n={"de": "Pass"}
    )
    db_session.add(candidate)
    db_session.flush()
    mention = DiscoveryCandidateMention(
        candidate_id=candidate.id,
        catalogue_service_id=catalogue.id,
        role=DiscoveryMentionRole.REQUIRED,
        excerpt="Pass",
        source_field="html",
        artifact_id=artifact.id,
        extractor="x",
        extractor_version="1",
    )
    db_session.add(mention)
    db_session.flush()

    db_session.delete(artifact)
    db_session.flush()
    db_session.refresh(task)
    db_session.refresh(mention)

    assert task.artifact_id is None
    assert mention.artifact_id is None


def test_task_result_note_defaults_to_none_and_render_page_is_a_task_kind(db_session: Session) -> None:
    catalogue = _catalogue_service(db_session)
    task = DiscoveryTask(
        catalogue_service_id=catalogue.id, kind=DiscoveryTaskKind.RENDER_PAGE, target_url="https://example.gov/page"
    )
    db_session.add(task)
    db_session.flush()
    db_session.refresh(task)

    assert task.kind is DiscoveryTaskKind.RENDER_PAGE
    assert task.result_note is None
    assert task.artifact_id is None


def _ledger_row(period: str, resource: str) -> DiscoveryBudgetLedger:
    return DiscoveryBudgetLedger(period=period, resource=resource, used=0)


def test_budget_ledger_allows_each_period_and_resource_once(db_session: Session) -> None:
    rows = [
        _ledger_row("2026-10-26", "browser_seconds"),
        _ledger_row("2026-10-27", "browser_seconds"),
        _ledger_row("2026-10-26", "neurons"),
    ]
    db_session.add_all(rows)
    db_session.flush()
    db_session.refresh(rows[0])

    assert rows[0].exhausted is False
    assert rows[0].used == 0
    assert rows[0].updated_at is not None


def test_budget_ledger_is_unique_per_period_and_resource(db_session: Session) -> None:
    db_session.add(_ledger_row("2026-10", "r2_class_a"))
    db_session.flush()
    db_session.add(_ledger_row("2026-10", "r2_class_a"))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_llm_extract_task_kind_and_issued_role_are_stored(db_session: Session) -> None:
    catalogue = _catalogue_service(db_session)
    candidate = _candidate(db_session, catalogue.jurisdiction_id)
    task = DiscoveryTask(
        catalogue_service_id=catalogue.id, kind=DiscoveryTaskKind.LLM_EXTRACT, target_url="https://example.gov/page"
    )
    mention = _mention(candidate, catalogue, role=DiscoveryMentionRole.ISSUED)
    db_session.add_all([task, mention])
    db_session.flush()
    db_session.expire_all()

    assert db_session.get(DiscoveryTask, task.id).kind is DiscoveryTaskKind.LLM_EXTRACT
    assert db_session.get(DiscoveryCandidateMention, mention.id).role is DiscoveryMentionRole.ISSUED


def test_mention_condition_and_code_columns_default_to_none(db_session: Session) -> None:
    catalogue = _catalogue_service(db_session)
    candidate = _candidate(db_session, catalogue.jurisdiction_id)
    mention = _mention(candidate, catalogue)
    db_session.add(mention)
    db_session.flush()
    db_session.expire_all()
    stored = db_session.get(DiscoveryCandidateMention, mention.id)

    assert (stored.condition, stored.is_optional, stored.category_codes) == (None, None, None)


def _edge(
    parent: DiscoveryDocumentCandidate, required: DiscoveryDocumentCandidate, catalogue: CatalogueService
) -> DiscoveryCandidateEdge:
    return DiscoveryCandidateEdge(
        parent_candidate_id=parent.id,
        required_candidate_id=required.id,
        catalogue_service_id=catalogue.id,
        excerpt="Personalausweis, Meldebescheinigung",
        basis=DiscoveryEdgeBasis.EXPLICIT,
        extractor="llm",
        extractor_version="1",
    )


def _two_candidates(session: Session, catalogue: CatalogueService) -> tuple[DiscoveryDocumentCandidate, ...]:
    parent = _candidate(session, catalogue.jurisdiction_id, key="reisepass")
    required = _candidate(session, catalogue.jurisdiction_id, key="meldebescheinigung")
    return parent, required


def test_edge_is_stored_with_optional_condition_unset(db_session: Session) -> None:
    catalogue = _catalogue_service(db_session)
    parent, required = _two_candidates(db_session, catalogue)
    edge = _edge(parent, required, catalogue)
    db_session.add(edge)
    db_session.flush()
    db_session.expire_all()
    stored = db_session.get(DiscoveryCandidateEdge, edge.id)

    assert stored.basis is DiscoveryEdgeBasis.EXPLICIT
    assert (stored.condition, stored.is_optional) == (None, None)


def test_edge_unique_per_parent_required_and_procedure(db_session: Session) -> None:
    catalogue = _catalogue_service(db_session)
    parent, required = _two_candidates(db_session, catalogue)
    db_session.add(_edge(parent, required, catalogue))
    db_session.flush()
    db_session.add(_edge(parent, required, catalogue))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_edge_with_equal_endpoints_is_rejected(db_session: Session) -> None:
    catalogue = _catalogue_service(db_session)
    parent, _ = _two_candidates(db_session, catalogue)
    db_session.add(_edge(parent, parent, catalogue))

    with pytest.raises(IntegrityError):
        db_session.flush()


@pytest.mark.parametrize("end", ["parent", "required"])
def test_deleting_a_candidate_cascades_its_edges(db_session: Session, end: str) -> None:
    catalogue = _catalogue_service(db_session)
    parent, required = _two_candidates(db_session, catalogue)
    edge = _edge(parent, required, catalogue)
    db_session.add(edge)
    db_session.flush()
    edge_id = edge.id

    db_session.delete(parent if end == "parent" else required)
    db_session.flush()
    db_session.expire_all()

    assert db_session.get(DiscoveryCandidateEdge, edge_id) is None
