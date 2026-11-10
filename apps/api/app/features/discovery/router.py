"""Litestar routers for discovery machine and admin APIs."""

from __future__ import annotations

from litestar import Request, Response, Router
from litestar.exceptions import HTTPException, ValidationException
from litestar.exceptions.responses import create_exception_response
from litestar.status_codes import (
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_507_INSUFFICIENT_STORAGE,
)
from litestar.types import ExceptionHandler, ExceptionHandlersMap

from app.features.discovery.admin_controller import DiscoveryAdminController
from app.features.discovery.artifact_admin_controller import DiscoveryArtifactAdminController
from app.features.discovery.artifact_machine_controller import DiscoveryArtifactMachineController
from app.features.discovery.budget_controllers import DiscoveryBudgetAdminController, DiscoveryBudgetMachineController
from app.features.discovery.candidate_admin_controller import DiscoveryCandidateAdminController
from app.features.discovery.candidate_machine_controller import DiscoveryCandidateMachineController
from app.features.discovery.dependencies import router_dependencies
from app.features.discovery.errors import (
    ArtifactTooLargeError,
    DiscoveryError,
    DiscoveryNotFoundError,
    InvalidDiscoveryInputError,
    StorageCapExceededError,
    TaskNotClaimedError,
    UnsupportedArtifactTypeError,
)
from app.features.discovery.machine_controller import DiscoveryMachineController
from app.features.discovery.taxonomy_machine_controller import DiscoveryTaxonomyMachineController
from app.features.search.errors import TaskNotOwnedError
from app.features.search.router import embedding_machine_router


def _invalid_payload_is_422(request: Request, exc: ValidationException) -> Response:
    exc.status_code = HTTP_422_UNPROCESSABLE_ENTITY
    return create_exception_response(request, exc)


def _not_found_is_404(request: Request, exc: DiscoveryNotFoundError) -> Response:
    return create_exception_response(request, HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(exc)))


def _invalid_input_is_422(request: Request, exc: InvalidDiscoveryInputError) -> Response:
    error = HTTPException(status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return create_exception_response(request, error)


def _answers_with(status_code: int) -> ExceptionHandler[DiscoveryError]:
    """Build a handler that answers a domain error with ``status_code`` and its message."""

    def handler(request: Request, exc: DiscoveryError) -> Response:
        error = HTTPException(status_code=status_code, detail=str(exc))
        return create_exception_response(request, error)

    return handler


DISCOVERY_ERROR_HANDLERS: ExceptionHandlersMap = {
    ArtifactTooLargeError: _answers_with(HTTP_413_REQUEST_ENTITY_TOO_LARGE),
    UnsupportedArtifactTypeError: _answers_with(HTTP_415_UNSUPPORTED_MEDIA_TYPE),
    StorageCapExceededError: _answers_with(HTTP_507_INSUFFICIENT_STORAGE),
    TaskNotClaimedError: _answers_with(HTTP_409_CONFLICT),
    TaskNotOwnedError: _answers_with(HTTP_409_CONFLICT),
    DiscoveryNotFoundError: _not_found_is_404,
    InvalidDiscoveryInputError: _invalid_input_is_422,
    ValidationException: _invalid_payload_is_422,
}

discovery_admin_router = Router(
    path="/api/v1/discovery/admin",
    route_handlers=[
        DiscoveryAdminController,
        DiscoveryCandidateAdminController,
        DiscoveryArtifactAdminController,
        DiscoveryBudgetAdminController,
    ],
    dependencies=router_dependencies,
    exception_handlers=DISCOVERY_ERROR_HANDLERS,
    tags=["discovery-admin"],
)

discovery_machine_router = Router(
    path="/api/v1/discovery/machine",
    route_handlers=[
        DiscoveryMachineController,
        DiscoveryCandidateMachineController,
        DiscoveryArtifactMachineController,
        DiscoveryBudgetMachineController,
        DiscoveryTaxonomyMachineController,
        embedding_machine_router,
    ],
    dependencies=router_dependencies,
    exception_handlers=DISCOVERY_ERROR_HANDLERS,
    tags=["discovery-machine"],
)
