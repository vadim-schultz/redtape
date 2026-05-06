"""Litestar router for the documents feature."""

from __future__ import annotations

from litestar import Router

from app.features.documents.controller import DocumentsController
from app.features.documents.dependencies import router_dependencies

documents_router = Router(
    path="/api/v1/documents",
    route_handlers=[DocumentsController],
    dependencies=router_dependencies,
    tags=["documents"],
)
