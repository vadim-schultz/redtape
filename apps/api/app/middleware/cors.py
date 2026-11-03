"""CORS policy, built once from the settings at import time."""

from __future__ import annotations

from litestar.config.cors import CORSConfig

from app.config import settings


def build_cors_config() -> CORSConfig:
    """Build CORS from the comma-separated origins setting, defaulting to the local web dev server."""
    origins = [o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()]
    if not origins:
        origins = ["http://localhost:5173"]

    return CORSConfig(
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )


cors_config = build_cors_config()
