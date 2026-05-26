from __future__ import annotations

from litestar import Controller, Request, get
from litestar.params import Parameter

from app.features.locations.service import LocationsService
from app.schema.location.read import LocationListResponse


def _request_locale(request: Request) -> str:
    state = request.scope.get("state") or {}
    return str(state.get("locale", "de"))


class LocationsController(Controller):
    """OpenPLZ-backed jurisdiction hierarchy endpoints."""

    path = "/"

    @get("/countries", sync_to_thread=True)
    def list_countries(
        self,
        request: Request,
        locations_service: LocationsService,
    ) -> LocationListResponse:
        locale = _request_locale(request)
        enabled: set[str] = getattr(request.app.state, "enabled_locale_codes", {"de", "en"})
        return locations_service.list_countries(locale=locale, enabled_locales=enabled)

    @get("/states", sync_to_thread=True)
    def list_states(
        self,
        request: Request,
        locations_service: LocationsService,
        country: str = Parameter(query="country"),
    ) -> LocationListResponse:
        locale = _request_locale(request)
        enabled: set[str] = getattr(request.app.state, "enabled_locale_codes", {"de", "en"})
        return locations_service.list_states(country_code=country, locale=locale, enabled_locales=enabled)

    @get("/districts", sync_to_thread=True)
    def list_districts(
        self,
        request: Request,
        locations_service: LocationsService,
        state_code: str = Parameter(query="state"),
    ) -> LocationListResponse:
        locale = _request_locale(request)
        enabled: set[str] = getattr(request.app.state, "enabled_locale_codes", {"de", "en"})
        return locations_service.list_districts(state_code=state_code, locale=locale, enabled_locales=enabled)

    @get("/cities", sync_to_thread=True)
    def list_cities(
        self,
        request: Request,
        locations_service: LocationsService,
        district: str = Parameter(query="district"),
    ) -> LocationListResponse:
        locale = _request_locale(request)
        enabled: set[str] = getattr(request.app.state, "enabled_locale_codes", {"de", "en"})
        return locations_service.list_cities(district_code=district, locale=locale, enabled_locales=enabled)

    @get("/localities", sync_to_thread=True)
    def list_localities(
        self,
        request: Request,
        locations_service: LocationsService,
        city: str = Parameter(query="city"),
    ) -> LocationListResponse:
        locale = _request_locale(request)
        enabled: set[str] = getattr(request.app.state, "enabled_locale_codes", {"de", "en"})
        return locations_service.list_localities(municipality_code=city, locale=locale, enabled_locales=enabled)
