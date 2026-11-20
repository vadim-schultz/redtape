"""Retention: prune fetch logs and events past the window, in bounded batches."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.features.discovery.repository import DiscoveryRepository
from app.features.discovery.repository.retention import PruneBatch

MAX_BATCHES = 100
"""The most batches one prune call runs; a larger backlog is cleared by the next call."""


class DiscoveryRetentionService:
    """Prune fetch logs and events past the retention window, batch by batch."""

    def __init__(
        self,
        repository: DiscoveryRepository,
        *,
        retention: timedelta,
        batch_size: int = 1000,
        max_batches: int = MAX_BATCHES,
    ) -> None:
        """Bind the service to ``repository`` with the window, the rows per batch and the batch cap of one call."""
        self._repo = repository
        self._retention = retention
        self._batch_size = batch_size
        self._max_batches = max_batches

    def prune(self, *, now: datetime) -> PruneBatch:
        """Delete what has aged out of the window before ``now``; stop at the first batch that is not full, or at the cap."""
        cutoff = now - self._retention
        totals = PruneBatch()
        for _ in range(self._max_batches):
            batch = self._repo.prune_batch(cutoff, limit=self._batch_size)
            totals = totals.plus(batch)
            if not batch.is_full(self._batch_size):
                break
        return totals
