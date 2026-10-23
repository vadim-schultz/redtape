"""Discovery staging ORM models."""

from __future__ import annotations

from app.models.discovery.catalogue_service import CatalogueService
from app.models.discovery.discovery_candidate_mention import DiscoveryCandidateMention
from app.models.discovery.discovery_claim import DiscoveryClaim
from app.models.discovery.discovery_document_candidate import DiscoveryDocumentCandidate
from app.models.discovery.discovery_entity import DiscoveryEntity
from app.models.discovery.discovery_event import DiscoveryEvent
from app.models.discovery.discovery_fetch_log import DiscoveryFetchLog
from app.models.discovery.discovery_run import DiscoveryRun
from app.models.discovery.discovery_task import DiscoveryTask
from app.models.discovery.enums import (
    LEGACY_TASK_KINDS,
    DiscoveryCandidateStatus,
    DiscoveryClaimKind,
    DiscoveryEventType,
    DiscoveryMentionRole,
    DiscoveryRunKind,
    DiscoveryRunStatus,
    DiscoverySource,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)

__all__ = [
    "LEGACY_TASK_KINDS",
    "CatalogueService",
    "DiscoveryCandidateMention",
    "DiscoveryCandidateStatus",
    "DiscoveryClaim",
    "DiscoveryClaimKind",
    "DiscoveryDocumentCandidate",
    "DiscoveryEntity",
    "DiscoveryEvent",
    "DiscoveryEventType",
    "DiscoveryFetchLog",
    "DiscoveryMentionRole",
    "DiscoveryRun",
    "DiscoveryRunKind",
    "DiscoveryRunStatus",
    "DiscoverySource",
    "DiscoveryTask",
    "DiscoveryTaskKind",
    "DiscoveryTaskStatus",
]
