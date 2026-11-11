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


def test_query_path_settings_load_defaults_and_accept_overrides() -> None:
    """config · query embedding neurons, index bypass, rate limit and proxy hops have safe defaults."""
    defaults = _settings()

    assert defaults.query_embed_neurons > 0
    assert defaults.search_vector_index_enabled is True
    assert defaults.search_rate_limit_per_minute > 0
    assert defaults.trusted_proxy_hops == 1
    assert (defaults.query_embed_breaker_failures, defaults.query_embed_breaker_cooldown_s) == (3, 30.0)

    tuned = _settings(search_vector_index_enabled=False, search_rate_limit_per_minute=5, trusted_proxy_hops=2)
    assert (tuned.search_vector_index_enabled, tuned.search_rate_limit_per_minute, tuned.trusted_proxy_hops) == (
        False,
        5,
        2,
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"query_embed_neurons": 0},
        {"search_rate_limit_per_minute": 0},
        {"trusted_proxy_hops": -1},
        {"query_embed_breaker_failures": 0},
        {"query_embed_breaker_cooldown_s": 0},
    ],
)
def test_query_path_settings_reject_invalid_values(overrides: dict[str, object]) -> None:
    """config · rejects a zero reservation, a zero rate limit and a negative hop count."""
    with pytest.raises(ValidationError):
        _settings(**overrides)


def test_embedding_locales_default_to_german_and_every_translation_target() -> None:
    """settings · EMBEDDING_LOCALES defaults to de plus the six targets and accepts a narrower list."""
    defaults = _settings()

    assert defaults.embedding_locale_codes == ("de", "en", "tr", "ru", "uk", "pl", "ro")
    assert _settings(embedding_locales="de, tr").embedding_locale_codes == ("de", "tr")
    assert _settings(embedding_locales="").embedding_locale_codes == ()


@pytest.mark.parametrize("value", ["de xx", "tr,tr", "klingon"])
def test_embedding_locales_with_an_unsupported_or_repeated_code_fails_at_load(value: str) -> None:
    """settings · EMBEDDING_LOCALES with an unsupported or repeated code fails at load."""
    with pytest.raises(ValidationError):
        _settings(embedding_locales=value)
