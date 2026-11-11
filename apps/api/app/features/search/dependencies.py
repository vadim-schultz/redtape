"""Dependency provider of the query embedder: one process-wide stack, so its cache is shared by all requests."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from litestar.params import Dependency

from app.config import settings
from app.db import SessionLocal
from app.features.search.embedder_budget import LedgerReservation
from app.features.search.embedder_factory import build_query_embedder
from app.features.search.query_embedder import QueryEmbedder

InjectedQueryEmbedder = Annotated[QueryEmbedder, Dependency(skip_validation=True)]
"""The ``query_embedder`` dependency as a provider parameter; Litestar cannot validate a plain Protocol."""


@lru_cache(maxsize=1)
def get_query_embedder() -> QueryEmbedder:
    """Build the query embedder from the settings once; its reservations commit in their own short transaction."""
    return build_query_embedder(settings, LedgerReservation(SessionLocal.begin, settings.query_embed_neurons))


def provide_query_embedder() -> QueryEmbedder:
    """Return the shared query embedder."""
    return get_query_embedder()
