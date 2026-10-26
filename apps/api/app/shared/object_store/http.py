"""Litestar mapping of object store availability errors to HTTP 503."""

from __future__ import annotations

from litestar import Request, Response
from litestar.exceptions import HTTPException
from litestar.exceptions.responses import create_exception_response
from litestar.status_codes import HTTP_503_SERVICE_UNAVAILABLE
from litestar.types import ExceptionHandlersMap

from app.shared.object_store.errors import ObjectStoreUnavailableError


def _unavailable_is_503(request: Request, exc: ObjectStoreUnavailableError) -> Response:
    error = HTTPException(status_code=HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    return create_exception_response(request, error)


object_store_exception_handlers: ExceptionHandlersMap = {ObjectStoreUnavailableError: _unavailable_is_503}
"""Also covers :class:`ObjectStoreQuotaError`, which extends the unavailable error."""
