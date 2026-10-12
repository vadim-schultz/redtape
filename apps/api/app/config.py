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

    @property
    def auth_enabled(self) -> bool:
        return self.supabase_jwks_url is not None and self.supabase_jwt_issuer is not None

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
