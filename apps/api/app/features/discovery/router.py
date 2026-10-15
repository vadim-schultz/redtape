"""Litestar routers for discovery machine and admin APIs."""

from __future__ import annotations

from litestar import Request, Response, Router
from litestar.exceptions import ValidationException
from litestar.exceptions.responses import create_exception_response
from litestar.status_codes import HTTP_422_UNPROCESSABLE_ENTITY

from app.features.discovery.admin_controller import DiscoveryAdminController
from app.features.discovery.dependencies import router_dependencies
from app.features.discovery.machine_controller import DiscoveryMachineController


def _invalid_payload_is_422(request: Request, exc: ValidationException) -> Response:
    exc.status_code = HTTP_422_UNPROCESSABLE_ENTITY
    return create_exception_response(request, exc)


discovery_admin_router = Router(
    path="/api/v1/discovery/admin",
    route_handlers=[DiscoveryAdminController],
    dependencies=router_dependencies,
    tags=["discovery-admin"],
)

discovery_machine_router = Router(
    path="/api/v1/discovery/machine",
    route_handlers=[DiscoveryMachineController],
    dependencies=router_dependencies,
    exception_handlers={ValidationException: _invalid_payload_is_422},
    tags=["discovery-machine"],
)
