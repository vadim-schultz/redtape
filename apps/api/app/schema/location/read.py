from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


JurisdictionKind = Literal["COUNTRY", "REGION", "MUNICIPALITY", "LOCALITY"]


class LocationNode(BaseModel):
    """Generic jurisdiction node returned by hierarchy endpoints."""

    model_config = ConfigDict(from_attributes=False)

    code: str
    name: str
    kind: JurisdictionKind
    openplz_type: str | None = None


class LocationListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    items: list[LocationNode] = Field(default_factory=list)

