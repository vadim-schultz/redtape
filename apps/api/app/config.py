from __future__ import annotations

from pydantic import Field
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

    @property
    def auth_enabled(self) -> bool:
        return self.supabase_jwks_url is not None and self.supabase_jwt_issuer is not None


settings = Settings()
