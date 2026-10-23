"""Litestar routers for discovery machine and admin APIs."""

from __future__ import annotations

from litestar import Request, Response, Router
from litestar.exceptions import HTTPException, ValidationException
from litestar.exceptions.responses import create_exception_response
from litestar.status_codes import HTTP_404_NOT_FOUND, HTTP_422_UNPROCESSABLE_ENTITY
from litestar.types import ExceptionHandlersMap

from app.features.discovery.admin_controller import DiscoveryAdminController
from app.features.discovery.candidate_machine_controller import DiscoveryCandidateMachineController
from app.features.discovery.dependencies import router_dependencies
from app.features.discovery.errors import DiscoveryNotFoundError, InvalidDiscoveryInputError
from app.features.discovery.machine_controller import DiscoveryMachineController


def _invalid_payload_is_422(request: Request, exc: ValidationException) -> Response:
    exc.status_code = HTTP_422_UNPROCESSABLE_ENTITY
    return create_exception_response(request, exc)


def _not_found_is_404(request: Request, exc: DiscoveryNotFoundError) -> Response:
    return create_exception_response(request, HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(exc)))


def _invalid_input_is_422(request: Request, exc: InvalidDiscoveryInputError) -> Response:
    error = HTTPException(status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return create_exception_response(request, error)


_DOMAIN_ERROR_HANDLERS: ExceptionHandlersMap = {
    DiscoveryNotFoundError: _not_found_is_404,
    InvalidDiscoveryInputError: _invalid_input_is_422,
}

discovery_admin_router = Router(
    path="/api/v1/discovery/admin",
    route_handlers=[DiscoveryAdminController],
    dependencies=router_dependencies,
    exception_handlers=_DOMAIN_ERROR_HANDLERS,
    tags=["discovery-admin"],
)

discovery_machine_router = Router(
    path="/api/v1/discovery/machine",
    route_handlers=[DiscoveryMachineController, DiscoveryCandidateMachineController],
    dependencies=router_dependencies,
    exception_handlers={**_DOMAIN_ERROR_HANDLERS, ValidationException: _invalid_payload_is_422},
    tags=["discovery-machine"],
)
