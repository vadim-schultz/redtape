"""Retention queries: prune fetch logs and events past the window, never the latest fetch of a target."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import ColumnElement, Select, delete, exists, select
from sqlalchemy.orm import aliased

from app.features.discovery.repository.base import SessionRepository
from app.models.discovery import DiscoveryEvent, DiscoveryFetchLog, DiscoveryTask


@dataclass(frozen=True, slots=True)
class PruneBatch:
    """Rows a prune deleted: fetch logs and events, from one batch or summed over several."""

    fetch_logs: int = 0
    events: int = 0

    def plus(self, other: PruneBatch) -> PruneBatch:
        """Return the rows of both batches added together."""
        return PruneBatch(fetch_logs=self.fetch_logs + other.fetch_logs, events=self.events + other.events)

    def is_full(self, limit: int) -> bool:
        """Return whether either table filled the batch, so that another batch may still find rows."""
        return max(self.fetch_logs, self.events) >= limit


def _has_newer_fetch_of_target() -> ColumnElement[bool]:
    """Return the predicate that a newer fetch exists for the same target: the same catalogue row and target URL."""
    newer_fetch = aliased(DiscoveryFetchLog)
    newer_task = aliased(DiscoveryTask)
    return exists().where(
        newer_task.id == newer_fetch.discovery_task_id,
        newer_task.catalogue_service_id == DiscoveryTask.catalogue_service_id,
        newer_task.target_url == DiscoveryTask.target_url,
        newer_fetch.fetched_at > DiscoveryFetchLog.fetched_at,
    )


def _prunable_fetch_ids(cutoff: datetime, limit: int) -> Select[tuple[uuid.UUID]]:
    """Return up to ``limit`` ids of fetch logs older than ``cutoff`` that have a newer fetch of their target."""
    return (
        select(DiscoveryFetchLog.id)
        .join(DiscoveryTask, DiscoveryTask.id == DiscoveryFetchLog.discovery_task_id)
        .where(DiscoveryFetchLog.fetched_at < cutoff, _has_newer_fetch_of_target())
        .limit(limit)
    )


def _expired_event_ids(cutoff: datetime, limit: int) -> Select[tuple[uuid.UUID]]:
    """Return up to ``limit`` ids of events created before ``cutoff``."""
    return select(DiscoveryEvent.id).where(DiscoveryEvent.created_at < cutoff).limit(limit)


class RetentionRepository(SessionRepository):
    """Delete the fetch logs and events that have aged out of the retention window."""

    def prune_batch(self, cutoff: datetime, *, limit: int) -> PruneBatch:
        """Delete up to ``limit`` aged-out fetch logs and up to ``limit`` aged-out events, keeping every target's latest fetch."""
        fetch_logs = self._session.scalars(
            delete(DiscoveryFetchLog)
            .where(DiscoveryFetchLog.id.in_(_prunable_fetch_ids(cutoff, limit)))
            .returning(DiscoveryFetchLog.id)
        ).all()
        events = self._session.scalars(
            delete(DiscoveryEvent)
            .where(DiscoveryEvent.id.in_(_expired_event_ids(cutoff, limit)))
            .returning(DiscoveryEvent.id)
        ).all()
        return PruneBatch(fetch_logs=len(fetch_logs), events=len(events))
