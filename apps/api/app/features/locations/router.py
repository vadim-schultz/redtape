"""Litestar router for the locations feature."""

from __future__ import annotations

from litestar import Router

from app.features.locations.controller import LocationsController
from app.features.locations.dependencies import router_dependencies

locations_router = Router(
    path="/api/v1",
    route_handlers=[LocationsController],
    dependencies=router_dependencies,
    tags=["locations"],
)
