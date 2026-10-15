"""Persistence for discovery admin reads and machine writes."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.features.discovery.url_normalize import normalize_canonical_url
from app.models.discovery import (
    CatalogueService,
    DiscoveryClaim,
    DiscoveryClaimKind,
    DiscoveryEntity,
    DiscoveryEvent,
    DiscoveryEventType,
    DiscoveryFetchLog,
    DiscoverySource,
    DiscoveryTask,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)
from app.schema.discovery.machine import CatalogueBatchItem


def _task_list_stmt(
    *,
    status: DiscoveryTaskStatus | None,
    source: DiscoverySource | None,
) -> Select:
    stmt = select(DiscoveryTask, CatalogueService.source).join(
        CatalogueService, DiscoveryTask.catalogue_service_id == CatalogueService.id
    )
    if status is not None:
        stmt = stmt.where(DiscoveryTask.status == status)
    if source is not None:
        stmt = stmt.where(CatalogueService.source == source)
    return stmt


def _catalogue_list_stmt(*, source: DiscoverySource | None) -> Select:
    stmt = select(CatalogueService)
    if source is not None:
        stmt = stmt.where(CatalogueService.source == source)
    return stmt


class DiscoveryRepository:
    """Discovery staging queries and machine-route persistence."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_catalogue_by_source_external_id(
        self, *, source: DiscoverySource, external_id: str
    ) -> CatalogueService | None:
        stmt = select(CatalogueService).where(
            CatalogueService.source == source,
            CatalogueService.external_id == external_id,
        )
        return self._session.scalar(stmt)

    def upsert_catalogue_item(self, item: CatalogueBatchItem) -> tuple[CatalogueService, bool]:
        """Insert or update a catalogue row; return the row and whether it was created."""

        existing = self.get_catalogue_by_source_external_id(source=item.source, external_id=item.external_id)
        if existing is None:
            row = CatalogueService(
                source=item.source,
                external_id=item.external_id,
                jurisdiction_id=item.jurisdiction_id,
                title_i18n=item.title_i18n,
                description_i18n=item.description_i18n,
                portal_url=item.portal_url,
                raw_payload=item.raw_payload,
                pipeline_stage="T0",
            )
            self._session.add(row)
            self._session.flush()
            return row, True
        existing.jurisdiction_id = item.jurisdiction_id
        existing.title_i18n = item.title_i18n
        existing.description_i18n = item.description_i18n
        existing.portal_url = item.portal_url
        existing.raw_payload = item.raw_payload
        self._session.flush()
        return existing, False

    def record_event(
        self,
        *,
        event_type: DiscoveryEventType,
        catalogue_service_id: UUID | None = None,
        discovery_task_id: UUID | None = None,
        payload: dict[str, object] | None = None,
    ) -> DiscoveryEvent:
        event = DiscoveryEvent(
            event_type=event_type,
            catalogue_service_id=catalogue_service_id,
            discovery_task_id=discovery_task_id,
            payload=payload or {},
        )
        self._session.add(event)
        self._session.flush()
        return event

    def find_pending_task(
        self,
        *,
        catalogue_service_id: UUID,
        kind: DiscoveryTaskKind,
        target_url: str,
    ) -> DiscoveryTask | None:
        stmt = (
            select(DiscoveryTask)
            .where(
                DiscoveryTask.catalogue_service_id == catalogue_service_id,
                DiscoveryTask.kind == kind,
                DiscoveryTask.target_url == target_url,
                DiscoveryTask.status == DiscoveryTaskStatus.PENDING,
            )
            .limit(1)
        )
        return self._session.scalar(stmt)

    def insert_task(
        self,
        *,
        catalogue_service_id: UUID,
        kind: DiscoveryTaskKind,
        target_url: str,
        priority: int = 100,
    ) -> DiscoveryTask:
        task = DiscoveryTask(
            catalogue_service_id=catalogue_service_id,
            kind=kind,
            target_url=target_url,
            status=DiscoveryTaskStatus.PENDING,
            priority=priority,
        )
        self._session.add(task)
        self._session.flush()
        return task

    def list_pending_tasks_for_claim(self, *, limit: int) -> list[DiscoveryTask]:
        stmt = (
            select(DiscoveryTask)
            .where(DiscoveryTask.status == DiscoveryTaskStatus.PENDING)
            .order_by(DiscoveryTask.priority.asc(), DiscoveryTask.created_at.asc(), DiscoveryTask.id.asc())
            .limit(limit)
        )
        return list(self._session.scalars(stmt).all())

    def get_task(self, task_id: UUID) -> DiscoveryTask | None:
        return self._session.get(DiscoveryTask, task_id)

    def append_fetch_log(
        self,
        *,
        task: DiscoveryTask,
        http_status: int | None,
        content_type: str | None,
        byte_length: int | None,
        error_message: str | None,
        fetched_at: datetime,
    ) -> DiscoveryFetchLog:
        row = DiscoveryFetchLog(
            discovery_task_id=task.id,
            http_status=http_status,
            content_type=content_type,
            byte_length=byte_length,
            error_message=error_message,
            fetched_at=fetched_at,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def count_tasks(
        self,
        *,
        status: DiscoveryTaskStatus | None = None,
        source: DiscoverySource | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(_task_list_stmt(status=status, source=source).subquery())
        return int(self._session.scalar(stmt) or 0)

    def list_tasks_page(
        self,
        *,
        offset: int,
        limit: int,
        status: DiscoveryTaskStatus | None = None,
        source: DiscoverySource | None = None,
    ) -> list[tuple[DiscoveryTask, DiscoverySource]]:
        stmt = _task_list_stmt(status=status, source=source)
        stmt = stmt.order_by(DiscoveryTask.priority.asc(), DiscoveryTask.created_at.asc(), DiscoveryTask.id.asc())
        stmt = stmt.offset(offset).limit(limit)
        return list(self._session.execute(stmt).tuples().all())

    def count_catalogue(self, *, source: DiscoverySource | None = None) -> int:
        stmt = select(func.count()).select_from(_catalogue_list_stmt(source=source).subquery())
        return int(self._session.scalar(stmt) or 0)

    def list_catalogue_page(
        self,
        *,
        offset: int,
        limit: int,
        source: DiscoverySource | None = None,
    ) -> list[CatalogueService]:
        stmt = _catalogue_list_stmt(source=source)
        stmt = stmt.order_by(CatalogueService.updated_at.desc(), CatalogueService.id.desc())
        stmt = stmt.offset(offset).limit(limit)
        return list(self._session.scalars(stmt).all())

    def catalogue_summary(self, *, source: DiscoverySource | None = None) -> tuple[int, dict[str, int], dict[str, int]]:
        base = _catalogue_list_stmt(source=source).subquery()
        total = int(self._session.scalar(select(func.count()).select_from(base)) or 0)
        by_source_rows = self._session.execute(select(base.c.source, func.count()).group_by(base.c.source)).all()
        by_stage_rows = self._session.execute(
            select(base.c.pipeline_stage, func.count()).group_by(base.c.pipeline_stage)
        ).all()
        by_source = {str(row[0]): int(row[1]) for row in by_source_rows}
        by_stage = {str(row[0]): int(row[1]) for row in by_stage_rows}
        return total, by_source, by_stage

    def get_catalogue(self, catalogue_id: UUID) -> CatalogueService | None:
        return self._session.get(CatalogueService, catalogue_id)

    def get_entity(self, entity_id: UUID) -> DiscoveryEntity | None:
        return self._session.get(DiscoveryEntity, entity_id)

    def upsert_entity(
        self,
        *,
        catalogue_service_id: UUID,
        canonical_url: str,
        label: str | None,
    ) -> tuple[DiscoveryEntity, bool]:
        """Insert or update an entity keyed by catalogue row and normalized canonical URL."""

        existing = self._find_entity_by_normalized_url(
            catalogue_service_id=catalogue_service_id,
            normalized_url=canonical_url,
        )
        if existing is not None:
            existing.canonical_url = canonical_url
            if label is not None and label.strip():
                existing.label = label
            self._session.flush()
            return existing, False
        row = DiscoveryEntity(
            catalogue_service_id=catalogue_service_id,
            canonical_url=canonical_url,
            label=label,
        )
        self._session.add(row)
        self._session.flush()
        return row, True

    def _find_entity_by_normalized_url(
        self,
        *,
        catalogue_service_id: UUID,
        normalized_url: str,
    ) -> DiscoveryEntity | None:
        for entity in self.list_catalogue_entities(catalogue_service_id):
            if normalize_canonical_url(entity.canonical_url) == normalized_url:
                return entity
        return None

    def append_claim(
        self,
        *,
        discovery_entity_id: UUID,
        kind: DiscoveryClaimKind,
        payload: dict[str, object],
        confidence: Decimal | None,
    ) -> DiscoveryClaim:
        row = DiscoveryClaim(
            discovery_entity_id=discovery_entity_id,
            kind=kind,
            payload=payload,
            confidence=confidence,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def list_catalogue_tasks(self, catalogue_id: UUID) -> list[tuple[DiscoveryTask, DiscoverySource]]:
        stmt = (
            select(DiscoveryTask, CatalogueService.source)
            .join(CatalogueService, DiscoveryTask.catalogue_service_id == CatalogueService.id)
            .where(DiscoveryTask.catalogue_service_id == catalogue_id)
            .order_by(DiscoveryTask.created_at.asc(), DiscoveryTask.id.asc())
        )
        return list(self._session.execute(stmt).tuples().all())

    def list_catalogue_events(self, catalogue_id: UUID) -> list[DiscoveryEvent]:
        stmt = (
            select(DiscoveryEvent)
            .where(DiscoveryEvent.catalogue_service_id == catalogue_id)
            .order_by(DiscoveryEvent.created_at.asc(), DiscoveryEvent.id.asc())
        )
        return list(self._session.scalars(stmt).all())

    def list_catalogue_entities(self, catalogue_id: UUID) -> list[DiscoveryEntity]:
        stmt = (
            select(DiscoveryEntity)
            .where(DiscoveryEntity.catalogue_service_id == catalogue_id)
            .order_by(DiscoveryEntity.created_at.asc(), DiscoveryEntity.id.asc())
        )
        return list(self._session.scalars(stmt).all())

    def list_catalogue_claims(self, catalogue_id: UUID) -> list[DiscoveryClaim]:
        stmt = (
            select(DiscoveryClaim)
            .join(DiscoveryEntity, DiscoveryClaim.discovery_entity_id == DiscoveryEntity.id)
            .where(DiscoveryEntity.catalogue_service_id == catalogue_id)
            .order_by(DiscoveryClaim.created_at.asc(), DiscoveryClaim.id.asc())
        )
        return list(self._session.scalars(stmt).all())

    def list_catalogue_fetch_logs(self, catalogue_id: UUID) -> list[DiscoveryFetchLog]:
        stmt = (
            select(DiscoveryFetchLog)
            .join(DiscoveryTask, DiscoveryFetchLog.discovery_task_id == DiscoveryTask.id)
            .where(DiscoveryTask.catalogue_service_id == catalogue_id)
            .order_by(DiscoveryFetchLog.fetched_at.asc(), DiscoveryFetchLog.id.asc())
        )
        return list(self._session.scalars(stmt).all())
