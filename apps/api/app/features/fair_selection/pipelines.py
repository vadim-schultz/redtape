"""Map each fair-selection pipeline to the task model and entity column its phase logic reads."""

from __future__ import annotations

from typing import TypeAlias
from uuid import UUID

from sqlalchemy.orm import InstrumentedAttribute

from app.models.discovery.discovery_task import DiscoveryTask
from app.models.search import EmbeddingTask
from app.models.snapshot_translation import SnapshotTranslationTask
from app.models.translation import TranslationTask

TaskModel: TypeAlias = type[TranslationTask] | type[EmbeddingTask] | type[DiscoveryTask] | type[SnapshotTranslationTask]

# Pipeline key -> (task model, entity-id column). The keys are the names fair_selection_state rows carry.
PIPELINE_TASKS: dict[str, tuple[TaskModel, InstrumentedAttribute[UUID]]] = {
    "translation": (TranslationTask, TranslationTask.candidate_id),
    "embedding": (EmbeddingTask, EmbeddingTask.candidate_id),
    "discovery": (DiscoveryTask, DiscoveryTask.catalogue_service_id),
    "snapshot_translation": (SnapshotTranslationTask, SnapshotTranslationTask.catalogue_service_id),
}
