"""Typed GovData payloads: OZG Leistungen rows and feed pages, and the CKAN package wrapper."""

from __future__ import annotations

from typing import Annotated, Self

from pydantic import BeforeValidator, Field, ModelWrapValidatorHandler, PrivateAttr, model_validator

from discovery_ingest.json_types import JsonObject
from discovery_ingest.lenient import (
    LenientText,
    WireModel,
    dict_or_none,
    dicts_only,
    dicts_or_none,
    first_present,
)


class GovDataRow(WireModel):
    """One OZG Leistungen row: the keys the mapper reads, plus the untouched row as ``raw``."""

    leika_key: LenientText = None
    ozgid: LenientText = None
    id: LenientText = None
    ars: LenientText = None
    leika_name: LenientText = None
    leistungsname: LenientText = None
    title_raw: LenientText = Field(default=None, alias="title")
    name_raw: LenientText = Field(default=None, alias="name")
    leika_bezeichnung: LenientText = None
    ozg_bezeichnung: LenientText = None
    beschreibung: LenientText = None
    description_raw: LenientText = Field(default=None, alias="description")
    url: LenientText = None
    _raw: JsonObject = PrivateAttr(default_factory=dict)

    @model_validator(mode="wrap")
    @classmethod
    def _keep_row(cls, data: object, handler: ModelWrapValidatorHandler[Self]) -> Self:
        """Keep a copy of the incoming row, so ``raw_payload`` is the row exactly as the feed sent it."""
        row = handler(data)
        if isinstance(data, dict):
            row._raw = dict(data)
        return row

    @property
    def raw(self) -> JsonObject:
        """Return a copy of the untouched row."""
        return dict(self._raw)

    @property
    def external_id_parts(self) -> tuple[str, str] | None:
        """Return the namespace and value of the external id: the LeiKa key, then the OZG id, then the row id."""
        if self.leika_key:
            return "leika", self.leika_key
        if self.ozgid:
            return "ozg", self.ozgid
        if self.id:
            return "ozg", self.id
        return None

    @property
    def title(self) -> str | None:
        """Return the first non-blank of the six title fields in mapping order."""
        return first_present(
            self.leika_name,
            self.leistungsname,
            self.title_raw,
            self.name_raw,
            self.leika_bezeichnung,
            self.ozg_bezeichnung,
        )

    @property
    def description(self) -> str | None:
        """Return the first non-blank of the four description fields in mapping order."""
        return first_present(
            self.beschreibung,
            self.description_raw,
            self.leika_bezeichnung,
            self.ozg_bezeichnung,
        )


class OzgPage(WireModel):
    """A feed page: its Leistungen rows; non-object rows are dropped and a missing array gives no rows."""

    content: Annotated[list[GovDataRow], BeforeValidator(dicts_only)] = Field(default_factory=list)


class CkanResource(WireModel):
    """A CKAN resource entry; only its id, name and URL are read."""

    id: LenientText = None
    name: LenientText = None
    url: LenientText = None


class CkanPackage(WireModel):
    """A CKAN package; ``resources`` is ``None`` when the package has no resources array."""

    resources: Annotated[list[CkanResource] | None, BeforeValidator(dicts_or_none)] = None


class CkanPackageShow(WireModel):
    """A CKAN ``package_show`` response; ``result`` is ``None`` when it is not an object."""

    result: Annotated[CkanPackage | None, BeforeValidator(dict_or_none)] = None
