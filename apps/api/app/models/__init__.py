"""Re-export the ORM models so callers import them from one place."""

from __future__ import annotations

from app.models.api_key import ApiKey
from app.models.base import Base
from app.models.discovery import (
    CatalogueService,
    DiscoveryClaim,
    DiscoveryClaimKind,
    DiscoveryEntity,
    DiscoveryEvent,
    DiscoveryEventType,
    DiscoveryFetchLog,
    DiscoveryRun,
    DiscoverySource,
    DiscoveryTask,
    DiscoveryTaskKind,
    DiscoveryTaskStatus,
)
from app.models.fair_selection_state import FairSelectionState
from app.models.document import Document, DocumentRequirement
from app.models.jurisdiction import Jurisdiction, JurisdictionKind
from app.models.locale import SupportedLocale, UITranslation
from app.models.locality import Locality
from app.models.search import (
    CandidateEmbedding,
    CandidateSearchText,
    EmbeddingTask,
    WorkTaskStatus,
)
from app.models.snapshot_translation import SnapshotTranslation, SnapshotTranslationTask
from app.models.suggestion import Suggestion, SuggestionKind, SuggestionSource, SuggestionStatus
from app.models.suggestion_event import EventType, SuggestionEvent
from app.models.suggestion_vote import SuggestionVote
from app.models.taxonomy import (
    Category,
    CategoryExternalMapping,
    DocumentExternalClassification,
)
from app.models.translation import CandidateTranslation, TranslationSource, TranslationTask
from app.models.user import AppUser, UserRole

__all__ = [
    "ApiKey",
    "AppUser",
    "Base",
    "CandidateEmbedding",
    "CandidateSearchText",
    "CandidateTranslation",
    "CatalogueService",
    "Category",
    "CategoryExternalMapping",
    "DiscoveryClaim",
    "DiscoveryClaimKind",
    "DiscoveryEntity",
    "DiscoveryEvent",
    "DiscoveryEventType",
    "DiscoveryFetchLog",
    "DiscoveryRun",
    "DiscoverySource",
    "DiscoveryTask",
    "DiscoveryTaskKind",
    "DiscoveryTaskStatus",
    "Document",
    "DocumentExternalClassification",
    "DocumentRequirement",
    "EmbeddingTask",
    "EventType",
    "FairSelectionState",
    "Jurisdiction",
    "JurisdictionKind",
    "Locality",
    "SnapshotTranslation",
    "SnapshotTranslationTask",
    "Suggestion",
    "SuggestionEvent",
    "SuggestionKind",
    "SuggestionSource",
    "SuggestionStatus",
    "SuggestionVote",
    "SupportedLocale",
    "TranslationSource",
    "TranslationTask",
    "UITranslation",
    "UserRole",
    "WorkTaskStatus",
]
