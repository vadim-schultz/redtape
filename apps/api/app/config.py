"""Application settings loaded from the environment and `.env`."""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.shared.locale import DEFAULT_LOCALE, SUPPORTED_LOCALE_CODES


class Settings(BaseSettings):
    """Application settings loaded from environment / `.env`."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/redtape",
        description=(
            "SQLAlchemy DSN (psycopg3). Override with DATABASE_URL in `.env`. "
            "Supabase: use the dashboard Shared/Session pooler host, user `postgres.<project_ref>`, "
            "database `postgres`, and `?sslmode=require` (see `.env.example`)."
        ),
    )

    cors_allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    supabase_jwks_url: str | None = Field(
        default=None,
        description="Supabase project JWKS URL, e.g. https://<project_ref>.supabase.co/auth/v1/.well-known/jwks.json",
    )
    supabase_jwt_issuer: str | None = Field(
        default=None,
        description="Supabase project JWT issuer, e.g. https://<project_ref>.supabase.co/auth/v1",
    )
    supabase_jwt_audience: str = "authenticated"

    vote_approve_threshold: int = 3
    vote_reject_threshold: int = -3

    discovery_admin_emails: str = Field(
        default="",
        description="Comma-separated emails allowed to call discovery admin routes (lowercase match).",
    )
    discovery_machine_opt_in: bool = Field(
        default=False,
        description="Enable discovery machine routes in dev when the admin allowlist is empty.",
    )

    object_store_endpoint_url: str | None = Field(
        default=None,
        description="S3 endpoint. Cloudflare R2: https://<account_id>.r2.cloudflarestorage.com (not a custom domain).",
    )
    object_store_region: str | None = Field(default=None, description="Signing region; `auto` for Cloudflare R2.")
    object_store_bucket: str | None = None
    object_store_access_key_id: str | None = None
    object_store_secret_access_key: str | None = Field(default=None, repr=False)
    object_store_force_path_style: bool = True
    object_store_max_bytes: int = Field(
        default=9_500_000_000,
        description="Ceiling for the sum of stored artifact bytes: 95 percent of the R2 free 10 GB; enforced on upload.",
    )

    budget_r2_class_a_monthly: int = Field(
        default=950_000,
        description="Monthly cap on R2 Class A operations (write, delete): 95 percent of the free 1M.",
    )
    budget_r2_class_b_monthly: int = Field(
        default=9_500_000,
        description="Monthly cap on R2 Class B operations (read, head): 95 percent of the free 10M.",
    )
    budget_browser_seconds_daily: int = Field(
        default=570,
        description="Daily cap on Cloudflare Browser Run seconds, all runs together: 95 percent of the free 600.",
    )
    budget_neurons_daily: int = Field(
        default=9_500,
        description="Daily cap on Workers AI neurons (extraction suite): 95 percent of the free 10,000.",
    )
    budget_azure_translator_chars_monthly: int = Field(
        default=1_900_000,
        description="Monthly cap on Azure AI Translator characters: 95 percent of the F0 free 2 million.",
    )
    budget_actions_minutes_monthly: int = Field(
        default=2_000,
        description=(
            "This repository's monthly GitHub Actions minutes, assuming this repository's share of the "
            "account-wide shared pool has grown to 2,000 (see gaps-and-decisions.md D1 — unverified)."
        ),
    )
    actions_ci_reserve_minutes: int = Field(
        default=1_000,
        description=(
            "Part of the monthly Actions minutes that CI keeps; drain workflows may not spend it. "
            "Split evenly with the scheduled-drain cap under the new 2,000-minute budget (D1/D2)."
        ),
    )
    db_soft_limit_bytes: int = Field(
        default=475_000_000,
        description="Database size above which machine write routes answer 507: 95 percent of the 500 MB read-only limit.",
    )

    embedding_model: str = Field(
        default="@cf/qwen/qwen3-embedding-0.6b",
        description="Workers AI embedding model; documents and queries must use the same one.",
    )
    embedding_dim: int = Field(
        default=1024,
        gt=0,
        description="Native output dimension of the model (chapter 1 probe); fixes the `halfvec(N)` width. The model ignores `dimensions`.",
    )
    search_hybrid_enabled: bool = Field(
        default=False,
        description="Serve hybrid (full-text + vector) search; off keeps keyword-only search.",
    )
    rrf_k: int = Field(default=60, gt=0, description="Reciprocal Rank Fusion constant `k` in `1 / (k + rank)`.")
    search_top_n: int = Field(default=50, gt=0, description="Candidates each search leg (keyword, vector) returns.")
    search_fused_top_k: int = Field(default=100, gt=0, description="Candidates kept after fusing the two legs.")
    search_min_similarity: float = Field(
        default=0.3,
        ge=0,
        le=1,
        description="Minimum cosine similarity (0..1) for a vector-leg hit; tuned in the search evaluation.",
    )
    search_confidence_weight: float = Field(
        default=0.3,
        ge=0,
        le=1,
        description=(
            "Weight `w` of confidence in the combined search score `(1 - w) * relevance + w * confidence`: "
            "0 ranks by relevance alone, 1 by confidence alone within the relevance pool; tuned in the search evaluation."
        ),
    )
    query_embed_timeout_s: float = Field(
        default=1.2,
        gt=0,
        description="Hard timeout in seconds for embedding one query; on expiry search degrades to keyword-only.",
    )
    query_embed_cache_size: int = Field(
        default=512, ge=0, description="Entries of the in-process query-embedding cache; 0 disables it."
    )
    query_embed_neurons: Decimal = Field(
        default=Decimal("0.1"),
        gt=0,
        decimal_places=2,
        description="Neurons reserved on the shared ledger for each uncached query embedding (the ledger counts hundredths).",
    )
    query_embed_breaker_failures: int = Field(
        default=3, gt=0, description="Consecutive query-embedding misses that open the circuit breaker."
    )
    query_embed_breaker_cooldown_s: float = Field(
        default=30.0,
        gt=0,
        description="Seconds the circuit breaker skips the embedder before it lets one probe through.",
    )
    search_vector_index_enabled: bool = Field(
        default=True,
        description="Let the vector leg use the HNSW index; false forces an exact scan, a setting for diagnosis.",
    )
    search_rate_limit_per_minute: int = Field(
        default=30, gt=0, description="Searches (list requests with `q`) one client may make per minute; then 429."
    )
    trusted_proxy_hops: int = Field(
        default=1,
        ge=0,
        description=(
            "Proxies in front of the API that each append the address they saw to `X-Forwarded-For`; the client is the "
            "entry that many places from the right. 0 ignores the header and uses the socket peer."
        ),
    )
    cloudflare_account_id: str = Field(
        default="", description="Cloudflare account id for query embedding; empty disables the query embedder."
    )
    cloudflare_ai_api_token: str = Field(
        default="",
        repr=False,
        description="Workers-AI-scoped token for query embedding; empty means search degrades to keyword-only.",
    )

    embedding_locales: str = Field(
        default="de en tr ru uk pl ro",
        description=(
            "Locales whose search text gets embedding tasks, separated by spaces or commas. A subset of the "
            "supported locales; search text and full-text vectors are written for every locale regardless. "
            "Dropping a locale stops new vectors; `scripts/prune_embeddings.py` reclaims the existing ones."
        ),
    )
    translation_target_locales: str = Field(
        default="en tr ru uk pl ro",
        description=(
            "Locales whose document text is translated, separated by spaces or commas. A subset of the supported "
            "locales without `de`; empty switches translation off. Translating a locale does not enable it for the UI."
        ),
    )
    translation_unit_recipe_version: str = Field(
        default="v1",
        min_length=1,
        description="Version of how a translation unit (title and card description) is built; bumping it makes every translation stale.",
    )

    @property
    def embedding_locale_codes(self) -> tuple[str, ...]:
        """Return the locale codes of :attr:`embedding_locales`, in order."""
        return tuple(self.embedding_locales.replace(",", " ").split())

    @property
    def translation_target_locale_codes(self) -> tuple[str, ...]:
        """Return the target locale codes of :attr:`translation_target_locales`, in order."""
        return tuple(self.translation_target_locales.replace(",", " ").split())

    @property
    def auth_enabled(self) -> bool:
        """Return whether JWT auth is on: both the Supabase JWKS URL and issuer are set."""
        return self.supabase_jwks_url is not None and self.supabase_jwt_issuer is not None

    @property
    def object_store_enabled(self) -> bool:
        """Return whether all five required object store values are set."""
        required = (
            self.object_store_endpoint_url,
            self.object_store_region,
            self.object_store_bucket,
            self.object_store_access_key_id,
            self.object_store_secret_access_key,
        )
        return all(required)

    @property
    def discovery_admin_email_set(self) -> frozenset[str]:
        """Return the admin emails from the comma-separated setting, lowercased and without blanks."""
        parts = [segment.strip().lower() for segment in self.discovery_admin_emails.split(",")]
        return frozenset(email for email in parts if email)

    @property
    def discovery_enabled(self) -> bool:
        """Return whether discovery is on: an admin email is configured or machine clients opted in."""
        return bool(self.discovery_admin_email_set) or self.discovery_machine_opt_in

    @model_validator(mode="after")
    def _check_translation_targets(self) -> Settings:
        codes = self.translation_target_locale_codes
        allowed = SUPPORTED_LOCALE_CODES - {DEFAULT_LOCALE}
        unknown = sorted(set(codes) - allowed)
        if unknown:
            raise ValueError(
                f"translation_target_locales: {unknown} are not target locales; allowed: {sorted(allowed)}"
            )
        if len(set(codes)) != len(codes):
            raise ValueError("translation_target_locales: a locale is listed twice")
        return self

    @model_validator(mode="after")
    def _check_embedding_locales(self) -> Settings:
        codes = self.embedding_locale_codes
        unknown = sorted(set(codes) - SUPPORTED_LOCALE_CODES)
        if unknown:
            raise ValueError(
                f"embedding_locales: {unknown} are not supported locales; allowed: {sorted(SUPPORTED_LOCALE_CODES)}"
            )
        if len(set(codes)) != len(codes):
            raise ValueError("embedding_locales: a locale is listed twice")
        return self

    @model_validator(mode="after")
    def _check_vote_thresholds(self) -> Settings:
        if self.vote_reject_threshold >= self.vote_approve_threshold:
            raise ValueError("vote_reject_threshold must be less than vote_approve_threshold")
        return self


settings = Settings()
