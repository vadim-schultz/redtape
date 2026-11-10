"""The neuron budget of query embedding: reserve before each uncached call, answer ``None`` when it is refused."""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import datetime
from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.features.discovery.budget_resources import BudgetResource
from app.features.discovery.budgets import BudgetService
from app.features.discovery.repository import DiscoveryRepository
from app.features.search.clock import Clock, utc_now
from app.features.search.query import NormalisedQuery
from app.features.search.query_embedder import QueryEmbedder, QueryVector

logger = logging.getLogger(__name__)

Reserve = Callable[[], bool]
"""Ask for the neurons of one query embedding; ``True`` when they were granted."""


class LedgerReservation:
    """Reserve ``amount`` neurons on the shared ledger in a short transaction of its own, committed before the call.

    A separate transaction keeps the ledger row lock away from the request's session and makes the spend durable
    even when the request later fails.
    """

    def __init__(
        self, sessions: Callable[[], AbstractContextManager[Session]], amount: Decimal, *, clock: Clock = utc_now
    ) -> None:
        """Open each reservation with ``sessions`` (a committing session scope) and ask for ``amount`` neurons."""
        self._sessions = sessions
        self._amount = amount
        self._clock: Callable[[], datetime] = clock

    def __call__(self) -> bool:
        """Return whether the ledger granted the neurons."""
        with self._sessions() as session:
            budget = BudgetService(DiscoveryRepository(session))
            return budget.reserve(BudgetResource.NEURONS, self._amount, self._clock()).granted


class BudgetedQueryEmbedder:
    """Call the wrapped embedder only after its neurons were reserved; a refused or failed reservation is ``None``."""

    def __init__(self, inner: QueryEmbedder, reserve: Reserve) -> None:
        """Wrap ``inner`` so every call first asks ``reserve``."""
        self._inner = inner
        self._reserve = reserve

    def embed(self, query: NormalisedQuery) -> QueryVector | None:
        """Return the vector of ``query``, or ``None`` when the budget refuses or cannot be consulted."""
        if not self._granted():
            return None
        return self._inner.embed(query)

    def _granted(self) -> bool:
        try:
            return self._reserve()
        except SQLAlchemyError:
            logger.warning("query embedding skipped: the neuron ledger could not be consulted", exc_info=True)
            return False
