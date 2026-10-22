from __future__ import annotations

from litestar import Controller, get
from litestar.params import Parameter

from app.features.locations.service import LocationsService
from app.schema.location.read import LocationListResponse
from app.shared.locale import ResolvedLocale


class LocationsController(Controller):
    """OpenPLZ-backed jurisdiction hierarchy endpoints."""

    path = "/"

    @get("/countries", sync_to_thread=True)
    def list_countries(
        self,
        locations_service: LocationsService,
        locale: ResolvedLocale,
    ) -> LocationListResponse:
        return locations_service.list_countries(locale=locale.code, enabled_locales=locale.enabled)

    @get("/states", sync_to_thread=True)
    def list_states(
        self,
        locations_service: LocationsService,
        locale: ResolvedLocale,
        country: str = Parameter(query="country"),
    ) -> LocationListResponse:
        return locations_service.list_states(country_code=country, locale=locale.code, enabled_locales=locale.enabled)

    @get("/districts", sync_to_thread=True)
    def list_districts(
        self,
        locations_service: LocationsService,
        locale: ResolvedLocale,
        state_code: str = Parameter(query="state"),
    ) -> LocationListResponse:
        return locations_service.list_districts(
            state_code=state_code, locale=locale.code, enabled_locales=locale.enabled
        )

    @get("/cities", sync_to_thread=True)
    def list_cities(
        self,
        locations_service: LocationsService,
        locale: ResolvedLocale,
        district: str = Parameter(query="district"),
    ) -> LocationListResponse:
        return locations_service.list_cities(district_code=district, locale=locale.code, enabled_locales=locale.enabled)

    @get("/localities", sync_to_thread=True)
    def list_localities(
        self,
        locations_service: LocationsService,
        locale: ResolvedLocale,
        city: str = Parameter(query="city"),
    ) -> LocationListResponse:
        return locations_service.list_localities(
            municipality_code=city, locale=locale.code, enabled_locales=locale.enabled
        )
