"""Litestar router for the auth feature."""

from __future__ import annotations

from litestar import Router

from app.features.auth.controller import MeController
from app.features.auth.dependencies import router_dependencies

auth_router = Router(
    path="/api/v1",
    route_handlers=[MeController],
    dependencies=router_dependencies,
    tags=["auth"],
)
