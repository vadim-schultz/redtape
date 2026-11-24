"""The identity of a discovery task: the target a caller names and the predicates that match an existing task to it."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import ColumnElement

from app.models.discovery import DiscoveryTask, DiscoveryTaskKind


@dataclass(frozen=True, slots=True)
class TaskTarget:
    """Identify a task by catalogue row, kind, target URL and optional input key; ``artifact_id`` is its input."""

    catalogue_service_id: UUID
    kind: DiscoveryTaskKind
    target_url: str
    input_key: str | None = None
    artifact_id: UUID | None = None


def identity_clauses(target: TaskTarget) -> tuple[ColumnElement[bool], ...]:
    """Return the predicates that name ``target``: its page, kind and input key, plus its artifact when it has one."""
    identity = (
        DiscoveryTask.catalogue_service_id == target.catalogue_service_id,
        DiscoveryTask.kind == target.kind,
        DiscoveryTask.target_url == target.target_url,
        DiscoveryTask.input_key == target.input_key,
    )
    if target.artifact_id is None:
        return identity
    return (*identity, DiscoveryTask.artifact_id == target.artifact_id)


@dataclass(frozen=True, slots=True)
class ExtractedText:
    """The page and versions a cleaned-text hash belongs to; an extraction is the same when all four match."""

    catalogue_service_id: UUID
    target_url: str
    input_key: str
    text_hash: str
