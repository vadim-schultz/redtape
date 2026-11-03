from __future__ import annotations

from app.features.locations.repository import LocationsRepository
from app.i18n_resolution import pick_i18n
from app.models.jurisdiction import JurisdictionKind
from app.models.locality import Locality
from app.schema.location.read import LocationListResponse, LocationNode
from app.shared.locale import ResolvedLocale


class LocationsService:
    def __init__(self, repository: LocationsRepository) -> None:
        self._repo = repository

    def list_countries(self, *, locale: ResolvedLocale) -> LocationListResponse:
        rows = self._repo.list_countries()
        items = [
            LocationNode(
                code=row.code or "",
                name=pick_i18n(row.name_i18n, locale),
                kind="COUNTRY",
                openplz_type=row.openplz_type,
            )
            for row in rows
            if row.code
        ]
        return LocationListResponse(items=items)

    def list_states(self, *, country_code: str, locale: ResolvedLocale) -> LocationListResponse:
        country = self._repo._get_jurisdiction_by_kind_and_code(kind=JurisdictionKind.COUNTRY, code=country_code)
        if country is None or country.id is None:
            return LocationListResponse(items=[])
        rows = self._repo.list_by_parent_and_kind(
            parent_id=country.id,
            kind=JurisdictionKind.REGION,
            administrative_role="REGION",
        )
        items = [
            LocationNode(
                code=row.code or "",
                name=pick_i18n(row.name_i18n, locale),
                kind="REGION",
                openplz_type=row.openplz_type,
            )
            for row in rows
            if row.code
        ]
        return LocationListResponse(items=items)

    def list_districts(self, *, state_code: str, locale: ResolvedLocale) -> LocationListResponse:
        state = self._repo._get_jurisdiction_by_kind_and_code(kind=JurisdictionKind.REGION, code=state_code)
        if state is None:
            return LocationListResponse(items=[])
        rows = self._repo.list_by_parent_and_kind(
            parent_id=state.id,
            kind=JurisdictionKind.REGION,
            administrative_role="DISTRICT",
        )
        items = [
            LocationNode(
                code=row.code or "",
                name=pick_i18n(row.name_i18n, locale),
                kind="REGION",
                openplz_type=row.openplz_type,
            )
            for row in rows
            if row.code
        ]
        return LocationListResponse(items=items)

    def list_cities(self, *, district_code: str, locale: ResolvedLocale) -> LocationListResponse:
        district = self._repo._get_jurisdiction_by_kind_and_code(kind=JurisdictionKind.REGION, code=district_code)
        if district is None:
            return LocationListResponse(items=[])
        rows = self._repo.list_by_parent_and_kind(
            parent_id=district.id,
            kind=JurisdictionKind.MUNICIPALITY,
        )
        items = [
            LocationNode(
                code=row.code or "",
                name=pick_i18n(row.name_i18n, locale),
                kind="MUNICIPALITY",
                openplz_type=row.openplz_type,
            )
            for row in rows
            if row.code
        ]
        return LocationListResponse(items=items)

    def list_localities(self, *, municipality_code: str, locale: ResolvedLocale) -> LocationListResponse:
        city = self._repo._get_jurisdiction_by_kind_and_code(kind=JurisdictionKind.MUNICIPALITY, code=municipality_code)
        if city is None:
            return LocationListResponse(items=[])
        rows: list[Locality] = self._repo.list_localities_for_city(municipality_id=city.id)
        items = [
            LocationNode(
                code=loc.postal_code,
                name=pick_i18n(loc.name_i18n, locale),
                kind="LOCALITY",
                openplz_type=None,
            )
            for loc in rows
        ]
        return LocationListResponse(items=items)
