"""Litestar router for the locales feature."""

from __future__ import annotations

from litestar import Router

from app.features.locales.controller import LocalesController
from app.features.locales.dependencies import router_dependencies

locales_router = Router(
    path="/api/v1",
    route_handlers=[LocalesController],
    dependencies=router_dependencies,
    tags=["locales"],
)
