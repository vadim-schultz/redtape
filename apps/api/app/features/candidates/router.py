"""Litestar router of the public candidate view: unguarded, with the metered object store."""

from __future__ import annotations

from litestar import Request, Response, Router
from litestar.status_codes import HTTP_404_NOT_FOUND

from app.features.candidates.controller import CandidatesController
from app.features.candidates.dependencies import router_dependencies
from app.features.discovery.router import DISCOVERY_ERROR_HANDLERS
from app.features.translation.errors import DocumentUnavailableError
from app.schema.candidate import DocumentTranslationError


def _document_unavailable(_: Request, exc: DocumentUnavailableError) -> Response[DocumentTranslationError]:
    """Answer 404 with the code, and the skip reason when there is one, so a client can tell the cases apart."""
    return Response(exc.body, status_code=HTTP_404_NOT_FOUND)


candidates_router = Router(
    path="/api/v1/candidates",
    route_handlers=[CandidatesController],
    dependencies=router_dependencies,
    exception_handlers={**DISCOVERY_ERROR_HANDLERS, DocumentUnavailableError: _document_unavailable},
    tags=["candidates"],
)
