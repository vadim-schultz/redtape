"""Pydantic DTOs for OpenPLZ Germany administrative data.

These models intentionally capture only the fields we need to normalize
OpenPLZ JSON into our internal `jurisdiction` + `locality` tables.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _OpenPLZBaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class OpenPLZFederalState(_OpenPLZBaseModel):
    """GET /{lang}/FederalStates item."""

    key: str
    name: str
    seat_of_government: str | None = Field(alias="seatOfGovernment", default=None)


class OpenPLZFederalStateRef(_OpenPLZBaseModel):
    key: str
    name: str


class OpenPLZDistrict(_OpenPLZBaseModel):
    """GET /{lang}/FederalStates/{stateCode}/Districts item."""

    key: str
    name: str
    type: str
    administrative_headquarters: str | None = Field(alias="administrativeHeadquarters", default=None)
    federalState: OpenPLZFederalStateRef | None = Field(alias="federalState", default=None)


class OpenPLZDistrictRef(_OpenPLZBaseModel):
    key: str
    name: str


class OpenPLZMunicipality(_OpenPLZBaseModel):
    """GET /{lang}/.../Municipalities item."""

    key: str
    name: str
    type: str

    postal_code: str | None = Field(alias="postalCode", default=None)
    multiple_postal_codes: bool = Field(alias="multiplePostalCodes", default=False)

    district: OpenPLZDistrictRef | None = Field(alias="district", default=None)


class OpenPLZMunicipalityRef(_OpenPLZBaseModel):
    key: str
    name: str


class OpenPLZLocality(_OpenPLZBaseModel):
    """GET /{lang}/Localities... item."""

    name: str
    postal_code: str = Field(alias="postalCode")
    municipality: OpenPLZMunicipalityRef | None = Field(alias="municipality", default=None)
