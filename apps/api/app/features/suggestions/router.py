"""Litestar router for the suggestions feature."""

from __future__ import annotations

from litestar import Request, Response, Router
from litestar.exceptions import ValidationException
from litestar.exceptions.responses import create_exception_response

from app.features.suggestions.controller import SuggestionsController
from app.features.suggestions.dependencies import router_dependencies


def _invalid_payload_is_422(request: Request, exc: ValidationException) -> Response:
    """Litestar's validation shape, at 422 instead of its default 400 (architecture §5)."""
    exc.status_code = 422
    return create_exception_response(request, exc)


suggestions_router = Router(
    path="/api/v1/suggestions",
    route_handlers=[SuggestionsController],
    dependencies=router_dependencies,
    exception_handlers={ValidationException: _invalid_payload_is_422},
    tags=["suggestions"],
)
