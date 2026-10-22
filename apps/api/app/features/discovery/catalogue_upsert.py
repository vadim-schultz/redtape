"""Catalogue upsert policy: insert-or-update, race recovery and rollback."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from app.features.discovery.db_errors import is_jurisdiction_foreign_key_violation
from app.features.discovery.errors import UnknownJurisdictionError
from app.features.discovery.pipeline import PipelineStage
from app.features.discovery.repository import DiscoveryRepository
from app.models.discovery import CatalogueService
from app.schema.discovery.machine import CatalogueBatchItem


class CatalogueUpsertService:
    """Insert or update catalogue rows, recovering from lost races."""

    def __init__(self, repository: DiscoveryRepository) -> None:
        """Bind the service to ``repository``."""
        self._repo = repository

    def upsert(self, item: CatalogueBatchItem) -> tuple[CatalogueService, bool]:
        """Insert or update a catalogue row; return the row and whether it was created."""
        existing = self._find(item)
        if existing is not None:
            return self._apply_fields(existing, item), False
        row = _new_row(item)
        try:
            self._repo.add_catalogue(row)
        except IntegrityError as exc:
            return self._recover_insert(exc, item)
        return row, True

    def _find(self, item: CatalogueBatchItem) -> CatalogueService | None:
        return self._repo.get_catalogue_by_source_external_id(source=item.source, external_id=item.external_id)

    def _recover_insert(self, exc: IntegrityError, item: CatalogueBatchItem) -> tuple[CatalogueService, bool]:
        self._reject_unknown_jurisdiction(exc, item)
        raced = self._find(item)
        if raced is None:
            raise exc
        return self._apply_fields(raced, item), False

    def _apply_fields(self, row: CatalogueService, item: CatalogueBatchItem) -> CatalogueService:
        _copy_fields(row, item)
        try:
            self._repo.flush()
        except IntegrityError as exc:
            self._reject_unknown_jurisdiction(exc, item)
            raise
        return row

    def _reject_unknown_jurisdiction(self, exc: IntegrityError, item: CatalogueBatchItem) -> None:
        self._repo.rollback()
        if is_jurisdiction_foreign_key_violation(exc):
            raise UnknownJurisdictionError(item.jurisdiction_id) from exc


def _copy_fields(row: CatalogueService, item: CatalogueBatchItem) -> None:
    row.jurisdiction_id = item.jurisdiction_id
    row.title_i18n = item.title_i18n
    row.description_i18n = item.description_i18n
    row.portal_url = item.portal_url
    row.raw_payload = item.raw_payload


def _new_row(item: CatalogueBatchItem) -> CatalogueService:
    return CatalogueService(
        source=item.source,
        external_id=item.external_id,
        jurisdiction_id=item.jurisdiction_id,
        title_i18n=item.title_i18n,
        description_i18n=item.description_i18n,
        portal_url=item.portal_url,
        raw_payload=item.raw_payload,
        pipeline_stage=PipelineStage.T0.value,
    )
