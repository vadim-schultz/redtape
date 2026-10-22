from __future__ import annotations

from litestar import Litestar
from litestar.di import Provide
from litestar.middleware.base import DefineMiddleware
from litestar.openapi.config import OpenAPIConfig
from litestar.plugins.pydantic import PydanticPlugin

from app.db import provide_session
from app.features.auth.router import auth_router
from app.features.discovery.router import discovery_admin_router, discovery_machine_router
from app.features.documents.router import documents_router
from app.features.locations.router import locations_router
from app.features.suggestions.router import suggestions_router
from app.features.taxonomy.router import taxonomy_router
from app.features.voting.router import voting_router
from app.lifespan import app_lifespan
from app.middleware.cors import cors_config
from app.middleware.locale import LocaleResolverMiddleware
from app.routes import health, list_locales, translations_bundle
from app.shared.dependencies import shared_dependencies


def create_app() -> Litestar:
    return Litestar(
        route_handlers=[
            health,
            list_locales,
            translations_bundle,
            auth_router,
            documents_router,
            discovery_admin_router,
            discovery_machine_router,
            locations_router,
            suggestions_router,
            taxonomy_router,
            voting_router,
        ],
        dependencies={"session": Provide(provide_session), **shared_dependencies},
        middleware=[DefineMiddleware(LocaleResolverMiddleware)],
        lifespan=[app_lifespan],
        cors_config=cors_config,
        openapi_config=OpenAPIConfig(title="RedTape API", version="0.1.0"),
        plugins=[PydanticPlugin()],
    )


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
