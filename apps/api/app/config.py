from __future__ import annotations

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    @property
    def auth_enabled(self) -> bool:
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
        parts = [segment.strip().lower() for segment in self.discovery_admin_emails.split(",")]
        return frozenset(email for email in parts if email)

    @property
    def discovery_enabled(self) -> bool:
        return bool(self.discovery_admin_email_set) or self.discovery_machine_opt_in

    @model_validator(mode="after")
    def _check_vote_thresholds(self) -> Settings:
        if self.vote_reject_threshold >= self.vote_approve_threshold:
            raise ValueError("vote_reject_threshold must be less than vote_approve_threshold")
        return self


settings = Settings()
