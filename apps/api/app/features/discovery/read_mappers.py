"""Map discovery ORM rows to their read models; plain functions, no queries."""

from __future__ import annotations

from app.features.taxonomy.compatibility import LegacyTaxonomyAdapter
from app.models.discovery import (
    CatalogueService,
    DiscoveryArtifact,
    DiscoveryCandidateMention,
    DiscoveryClaim,
    DiscoveryDocumentCandidate,
    DiscoveryEntity,
    DiscoveryEvent,
    DiscoveryFetchLog,
    DiscoverySource,
    DiscoveryTask,
)
from app.schema.discovery.artifacts import ArtifactRead, ArtifactSummaryRead
from app.schema.discovery.candidates import PvogSourcePath
from app.schema.discovery.read import (
    CandidateMentionRead,
    CandidateRead,
    CatalogueServiceRead,
    ClaimRow,
    DiscoveryTaskRead,
    EventRow,
    FetchLogRow,
    PipelineEntityRow,
)


def task_read(task: DiscoveryTask, *, source: DiscoverySource) -> DiscoveryTaskRead:
    """Return the admin view of ``task`` queued for ``source``."""
    return DiscoveryTaskRead(
        id=task.id,
        catalogue_service_id=task.catalogue_service_id,
        source=source,
        kind=task.kind,
        target_url=task.target_url,
        status=task.status,
        priority=task.priority,
        attempt_count=task.attempt_count,
        not_before=task.not_before,
        input_key=task.input_key,
        result_note=task.result_note,
        lease_expires_at=task.lease_expires_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def catalogue_read(row: CatalogueService) -> CatalogueServiceRead:
    """Return the admin index view of one catalogue row."""
    return CatalogueServiceRead(
        id=row.id,
        source=row.source,
        external_id=row.external_id,
        jurisdiction_id=row.jurisdiction_id,
        title_i18n=row.title_i18n,
        pipeline_stage=row.pipeline_stage,
        portal_url=row.portal_url,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def candidate_read(row: DiscoveryDocumentCandidate, *, mention_count: int) -> CandidateRead:
    """Return the view of a candidate with the number of procedures mentioning it."""
    return CandidateRead(
        id=row.id,
        jurisdiction_id=row.jurisdiction_id,
        key=row.key,
        title_i18n=row.title_i18n,
        official_url=row.official_url,
        status=row.status,
        suggestion_id=row.suggestion_id,
        mention_count=mention_count,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def mention_read(
    mention: DiscoveryCandidateMention, procedure: CatalogueService, artifact: DiscoveryArtifact | None
) -> CandidateMentionRead:
    """Return one mention with the procedure it was found in and its artifact summary."""
    category_resolution = LegacyTaxonomyAdapter().canonical_code_resolution(
        domain_codes=mention.domain_codes or (),
        situation_codes=mention.situation_codes or (),
    )
    source_path, mapping_version = _pvog_provenance(mention, procedure)
    return CandidateMentionRead(
        id=mention.id,
        catalogue_service_id=procedure.id,
        procedure_title_i18n=procedure.title_i18n,
        procedure_source=procedure.source,
        portal_url=procedure.portal_url,
        role=mention.role,
        excerpt=mention.excerpt,
        source_field=mention.source_field,
        artifact_id=mention.artifact_id,
        artifact=artifact_summary_read(artifact) if artifact else None,
        extractor=mention.extractor,
        extractor_version=mention.extractor_version,
        condition=mention.condition,
        is_optional=mention.is_optional,
        category_codes=list(category_resolution.codes),
        unknown_category_codes=list(category_resolution.unknown_codes),
        pvog_leaf_code=mention.pvog_leaf_code,
        direct_category_confidence=mention.direct_category_confidence,
        pvog_source_path=source_path,
        pvog_mapping_version=mapping_version,
        created_at=mention.created_at,
    )


def _pvog_provenance(
    mention: DiscoveryCandidateMention, procedure: CatalogueService
) -> tuple[PvogSourcePath | None, str | None]:
    """Read typed PVOG provenance from the mention or its source row during the storage transition."""
    path_data = mention.pvog_source_path
    path: PvogSourcePath | None = None
    if path_data is not None:
        path = PvogSourcePath.model_validate(path_data)
    mapping_version = mention.pvog_mapping_version
    raw_path = procedure.raw_payload.get("_pvog_source_path")
    if path is None and isinstance(raw_path, dict):
        try:
            path = PvogSourcePath.model_validate(raw_path)
        except ValueError:
            path = None
    raw_version = procedure.raw_payload.get("_pvog_category_mapping_version")
    if mapping_version is None and isinstance(raw_version, str):
        mapping_version = raw_version
    return path, mapping_version


def artifact_read(row: DiscoveryArtifact) -> ArtifactRead:
    """Return the metadata view of ``row``; the bytes stay in the object store."""
    return ArtifactRead(
        id=row.id,
        catalogue_service_id=row.catalogue_service_id,
        discovery_task_id=row.discovery_task_id,
        kind=row.kind,
        storage_key=row.storage_key,
        sha256=row.sha256,
        content_type=row.content_type,
        byte_size=row.byte_size,
        source_url=row.source_url,
        final_url=row.final_url,
        fetched_at=row.fetched_at,
        created_at=row.created_at,
    )


def artifact_summary_read(row: DiscoveryArtifact) -> ArtifactSummaryRead:
    """Return the few artifact fields a mention shows."""
    return ArtifactSummaryRead(id=row.id, kind=row.kind, fetched_at=row.fetched_at)


def entity_row(row: DiscoveryEntity) -> PipelineEntityRow:
    """Return the pipeline view of a staged entity."""
    return PipelineEntityRow(
        id=row.id,
        catalogue_service_id=row.catalogue_service_id,
        canonical_url=row.canonical_url,
        label=row.label,
        created_at=row.created_at,
    )


def fetch_log_row(row: DiscoveryFetchLog) -> FetchLogRow:
    """Return the pipeline view of one fetch attempt."""
    return FetchLogRow(
        id=row.id,
        discovery_task_id=row.discovery_task_id,
        http_status=row.http_status,
        fetched_at=row.fetched_at,
        content_type=row.content_type,
        byte_length=row.byte_length,
        error_message=row.error_message,
    )


def claim_row(row: DiscoveryClaim) -> ClaimRow:
    """Return the pipeline view of a claim; confidence is a float on the wire."""
    return ClaimRow(
        id=row.id,
        discovery_entity_id=row.discovery_entity_id,
        kind=row.kind,
        payload=row.payload,
        confidence=float(row.confidence) if row.confidence is not None else None,
        created_at=row.created_at,
    )


def event_row(row: DiscoveryEvent) -> EventRow:
    """Return the pipeline view of one audit event."""
    return EventRow(
        id=row.id,
        event_type=row.event_type,
        catalogue_service_id=row.catalogue_service_id,
        discovery_task_id=row.discovery_task_id,
        payload=row.payload,
        created_at=row.created_at,
    )
