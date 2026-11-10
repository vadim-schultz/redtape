"""Search and embedding settings: documented defaults, overrides and validation at load."""

from __future__ import annotations

import pytest
from app.config import Settings
from pydantic import ValidationError


def _settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[arg-type]


def test_search_settings_load_defaults_and_accept_overrides() -> None:
    """config · search settings load defaults and accept overrides."""
    defaults = _settings()

    assert defaults.embedding_model == "@cf/qwen/qwen3-embedding-0.6b"
    assert defaults.embedding_dim > 0
    assert defaults.search_hybrid_enabled is False
    assert (defaults.rrf_k, defaults.search_top_n, defaults.search_fused_top_k) == (60, 50, 100)
    assert 0 <= defaults.search_min_similarity <= 1
    assert defaults.query_embed_timeout_s > 0
    assert defaults.query_embed_cache_size > 0
    assert (defaults.cloudflare_account_id, defaults.cloudflare_ai_api_token) == ("", "")

    tuned = _settings(
        embedding_dim=512,
        search_hybrid_enabled=True,
        rrf_k=20,
        search_min_similarity=0.5,
        cloudflare_account_id="acc",
        cloudflare_ai_api_token="tok",
    )
    assert (tuned.embedding_dim, tuned.search_hybrid_enabled, tuned.rrf_k) == (512, True, 20)
    assert (tuned.search_min_similarity, tuned.cloudflare_account_id) == (0.5, "acc")


@pytest.mark.parametrize(
    "overrides",
    [
        {"embedding_dim": 0},
        {"embedding_dim": -1},
        {"rrf_k": 0},
        {"search_top_n": 0},
        {"search_fused_top_k": 0},
        {"search_min_similarity": -0.01},
        {"search_min_similarity": 1.01},
        {"query_embed_timeout_s": 0},
        {"query_embed_cache_size": -1},
    ],
)
def test_search_settings_reject_an_invalid_dimension_k_or_similarity(overrides: dict[str, object]) -> None:
    """config · rejects an invalid dimension, k or similarity at load."""
    with pytest.raises(ValidationError):
        _settings(**overrides)


def test_the_ai_token_is_not_shown_in_the_settings_repr() -> None:
    """config · the Workers AI token stays out of logs and tracebacks."""
    assert "super-secret" not in repr(_settings(cloudflare_ai_api_token="super-secret"))
