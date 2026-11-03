"""Typed PVOG Suchdienst payloads: the facades bootstrap, one search page and one service row."""

from __future__ import annotations

from typing import Annotated, Self

from pydantic import BeforeValidator, Field, ModelWrapValidatorHandler, PrivateAttr, model_validator

from discovery_ingest.json_types import JsonObject, JsonValue
from discovery_ingest.lenient import (
    LenientText,
    StrText,
    WireModel,
    dict_or_empty,
    dict_or_none,
    dicts_only,
    first_present,
    list_or_empty,
    optional_str,
    text_or_none,
)


class PersonalMatterNode(WireModel):
    """One node of the Lebenslagen tree: its code and its children."""

    code: StrText = None
    children: Annotated[list[PersonalMatterNode], BeforeValidator(dicts_only)] = Field(default_factory=list)
    _has_children: bool = PrivateAttr(default=False)

    @model_validator(mode="wrap")
    @classmethod
    def _note_children(cls, data: object, handler: ModelWrapValidatorHandler[Self]) -> Self:
        """Remember whether the raw ``children`` array is non-empty, because a node with children is not a leaf."""
        node = handler(data)
        if isinstance(data, dict):
            raw_children = data.get("children")
            node._has_children = isinstance(raw_children, list) and bool(raw_children)
        return node

    def leaf_codes(self) -> list[str]:
        """Return the stripped leaf codes below this node, or its own code when it is a leaf."""
        if self._has_children:
            return [code for child in self.children for code in child.leaf_codes()]
        return [self.code] if self.code else []


class PvogFacades(WireModel):
    """The ``facades`` object of the bootstrap page; only the personal matter tree is read."""

    personal_matters: Annotated[list[PersonalMatterNode], BeforeValidator(dicts_only)] = Field(
        default_factory=list, alias="personalMatters"
    )


class PvogBootstrap(WireModel):
    """The facades bootstrap page: the whole Lebenslagen tree for one jurisdiction."""

    facades: Annotated[PvogFacades, BeforeValidator(dict_or_empty)] = Field(default_factory=PvogFacades)

    def leaf_codes(self) -> list[str]:
        """Return the sorted, unique leaf personal matter codes."""
        codes = [code for node in self.facades.personal_matters for code in node.leaf_codes()]
        return sorted(set(codes))


class PvogLink(WireModel):
    """A link entry of a service row; only its URI is read."""

    uri: LenientText = None


class PvogRecord(WireModel):
    """One service row of a search page: the keys the mapper reads, plus the untouched row as ``raw``."""

    id: JsonValue = None
    lb_id_value: JsonValue = Field(default=None, alias="lbId")
    leika_keys: Annotated[list[LenientText], BeforeValidator(list_or_empty)] = Field(
        default_factory=list, alias="leikakeys"
    )
    leika_ids: Annotated[list[LenientText], BeforeValidator(list_or_empty)] = Field(
        default_factory=list, alias="leikaIds"
    )
    online_service_links: Annotated[list[PvogLink], BeforeValidator(dicts_only)] = Field(
        default_factory=list, alias="onlineServiceLinks"
    )
    source_portals: Annotated[list[PvogLink], BeforeValidator(dicts_only)] = Field(
        default_factory=list, alias="sourcePortals"
    )
    title_raw: LenientText = Field(default=None, alias="title")
    name_raw: LenientText = Field(default=None, alias="name")
    leistungsname: LenientText = None
    description_raw: LenientText = Field(default=None, alias="description")
    beschreibung: LenientText = None
    teaser: LenientText = None
    _raw: JsonObject = PrivateAttr(default_factory=dict)

    @model_validator(mode="wrap")
    @classmethod
    def _keep_row(cls, data: object, handler: ModelWrapValidatorHandler[Self]) -> Self:
        """Keep a copy of the incoming row, so ``raw_payload`` is the row exactly as the service sent it."""
        record = handler(data)
        if isinstance(data, dict):
            record._raw = dict(data)
        return record

    @property
    def raw(self) -> JsonObject:
        """Return a copy of the untouched row."""
        return dict(self._raw)

    @property
    def dedupe_id(self) -> str | None:
        """Return the first non-blank string ``id`` or ``lbId``, used to skip rows already seen in a walk."""
        return first_present(text_or_none(self.id), text_or_none(self.lb_id_value))

    @property
    def lb_id(self) -> str | None:
        """Return the first non-blank ``id`` or ``lbId`` as text, coercing non-strings (the external id)."""
        return first_present(optional_str(self.id), optional_str(self.lb_id_value))

    @property
    def leika_key(self) -> str | None:
        """Return the first non-blank LeiKa key from ``leikakeys``, then ``leikaIds``."""
        return first_present(*self.leika_keys, *self.leika_ids)

    @property
    def portal_url(self) -> str | None:
        """Return the first non-blank link URI of the online service links, then of the source portals."""
        return first_present(
            *(link.uri for link in self.online_service_links), *(link.uri for link in self.source_portals)
        )

    @property
    def title(self) -> str | None:
        """Return the first non-blank of ``title``, ``name`` and ``leistungsname``."""
        return first_present(self.title_raw, self.name_raw, self.leistungsname)

    @property
    def description(self) -> str | None:
        """Return the first non-blank of ``description``, ``beschreibung`` and ``teaser``."""
        return first_present(self.description_raw, self.beschreibung, self.teaser)


class PvogServicePage(WireModel):
    """The ``serviceDescriptions`` wrapper of a search page: its rows and the last-page flag."""

    content: Annotated[list[PvogRecord], BeforeValidator(dicts_only)] = Field(default_factory=list)
    last: JsonValue = True

    @property
    def is_last(self) -> bool:
        """Return the truthiness of ``last``; a missing flag counts as the last page."""
        return bool(self.last)


class PvogPage(WireModel):
    """A search page; a page without a ``serviceDescriptions`` object has no rows and is the last page."""

    service_descriptions: Annotated[PvogServicePage | None, BeforeValidator(dict_or_none)] = Field(
        default=None, alias="serviceDescriptions"
    )

    @property
    def records_and_last(self) -> tuple[list[PvogRecord], bool]:
        """Return the rows of the page and whether it is the last one."""
        if self.service_descriptions is None:
            return [], True
        return self.service_descriptions.content, self.service_descriptions.is_last
