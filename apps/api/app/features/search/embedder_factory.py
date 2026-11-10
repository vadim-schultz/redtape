"""Build the query-embedder stack of a deployment: cache, breaker, budget, then Workers AI, or the stand-in."""

from __future__ import annotations

import httpx

from app.config import Settings
from app.features.search.cloudflare_embedder import CloudflareQueryEmbedder
from app.features.search.embedder_breaker import CircuitBreakerQueryEmbedder
from app.features.search.embedder_budget import BudgetedQueryEmbedder, Reserve
from app.features.search.embedder_cache import CachedQueryEmbedder
from app.features.search.query_embedder import QueryEmbedder, UnavailableQueryEmbedder


def build_query_embedder(config: Settings, reserve: Reserve, *, http: httpx.Client | None = None) -> QueryEmbedder:
    """Return the embedder for ``config``: without both Workers AI credentials nothing is ever embedded."""
    if not (config.cloudflare_account_id and config.cloudflare_ai_api_token):
        return UnavailableQueryEmbedder()
    provider = CloudflareQueryEmbedder(
        config.cloudflare_account_id,
        config.cloudflare_ai_api_token,
        config.embedding_model,
        dim=config.embedding_dim,
        timeout_s=config.query_embed_timeout_s,
        http=http,
    )
    guarded = CircuitBreakerQueryEmbedder(
        BudgetedQueryEmbedder(provider, reserve),
        failures=config.query_embed_breaker_failures,
        cooldown_s=config.query_embed_breaker_cooldown_s,
    )
    return CachedQueryEmbedder(guarded, config.embedding_model, size=config.query_embed_cache_size)
