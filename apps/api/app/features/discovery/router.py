"""Litestar routers for discovery machine and admin APIs."""

from __future__ import annotations

from litestar import Router

from app.features.discovery.admin_controller import DiscoveryAdminController
from app.features.discovery.dependencies import router_dependencies

discovery_admin_router = Router(
    path="/api/v1/discovery/admin",
    route_handlers=[DiscoveryAdminController],
    dependencies=router_dependencies,
    tags=["discovery-admin"],
)
