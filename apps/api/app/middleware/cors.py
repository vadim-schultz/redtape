from __future__ import annotations

from litestar.config.cors import CORSConfig

from app.config import settings


def build_cors_config() -> CORSConfig:
    origins = [o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()]
    if not origins:
        origins = ["http://localhost:5173"]

    # MVP convenience: allow the Cloudflare Pages origin used by this plan.
    # If you change the Pages project name/custom domain, update `CORS_ALLOWED_ORIGINS`.
    prod_pages_origin = "https://redtape-web.pages.dev"
    if prod_pages_origin not in origins:
        origins.append(prod_pages_origin)

    return CORSConfig(
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )


cors_config = build_cors_config()
