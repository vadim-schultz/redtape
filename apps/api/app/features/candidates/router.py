"""Litestar router of the public candidate view: unguarded, with the metered object store."""

from __future__ import annotations

from litestar import Router

from app.features.candidates.controller import CandidatesController
from app.features.candidates.dependencies import router_dependencies
from app.features.discovery.router import DISCOVERY_ERROR_HANDLERS

candidates_router = Router(
    path="/api/v1/candidates",
    route_handlers=[CandidatesController],
    dependencies=router_dependencies,
    exception_handlers=DISCOVERY_ERROR_HANDLERS,
    tags=["candidates"],
)
