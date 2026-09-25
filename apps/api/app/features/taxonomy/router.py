"""Litestar router for the taxonomy feature."""

from __future__ import annotations

from litestar import Router

from app.features.taxonomy.controller import TaxonomyController
from app.features.taxonomy.dependencies import router_dependencies

taxonomy_router = Router(
    path="/api/v1",
    route_handlers=[TaxonomyController],
    dependencies=router_dependencies,
    tags=["taxonomy"],
)
