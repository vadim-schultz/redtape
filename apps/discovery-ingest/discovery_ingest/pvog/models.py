"""Typed PVOG Suchdienst payloads: the facades bootstrap, one search page and one service row."""

from __future__ import annotations

from typing import Annotated, Self

from pydantic import AliasChoices, BeforeValidator, Field, ModelWrapValidatorHandler, PrivateAttr, model_validator

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


class PvogSourcePath(WireModel):
    """The root, parent and leaf path discovered in a PVOG bootstrap tree."""

    root_code: StrText = None
    root_label: LenientText = None
    parent_code: StrText = None
    parent_label: LenientText = None
    leaf_code: StrText = None
    leaf_label: LenientText = None
    source_version: LenientText = None

    @property
    def has_parent_path(self) -> bool:
        """Return whether the path has the identifiers needed for source mapping."""
        return bool(self.root_code and self.parent_code and self.leaf_code)

    def as_raw(self) -> JsonObject:
        """Return the populated path fields for inclusion in a raw source payload."""
        values: JsonObject = {}
        for key, value in (
            ("root_code", self.root_code),
            ("root_label", self.root_label),
            ("parent_code", self.parent_code),
            ("parent_label", self.parent_label),
            ("leaf_code", self.leaf_code),
            ("leaf_label", self.leaf_label),
            ("source_version", self.source_version),
        ):
            if value:
                values[key] = value
        return values


class PersonalMatterNode(WireModel):
    """One node of the Lebenslagen tree: its code, label and children."""

    code: StrText = None
    label: LenientText = Field(
        default=None,
        validation_alias=AliasChoices("label", "name", "title"),
    )
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
    source_version: LenientText = Field(
        default=None,
        validation_alias=AliasChoices("sourceVersion", "version", "apiVersion"),
    )

    def leaf_codes(self) -> list[str]:
        """Return the sorted, unique leaf personal matter codes."""
        codes = [code for node in self.facades.personal_matters for code in node.leaf_codes()]
        return sorted(set(codes))

    def leaf_paths(self) -> dict[str, PvogSourcePath]:
        """Return each leaf code with its discovered root/parent path and source version."""
        paths: dict[str, PvogSourcePath] = {}
        for root in self.facades.personal_matters:
            _collect_leaf_paths(root, root=root, parent=None, source_version=self.source_version, paths=paths)
        return paths

    def path_for(self, leaf_code: str) -> PvogSourcePath:
        """Return the source path for ``leaf_code`` or fail when it is absent."""
        try:
            return self.leaf_paths()[leaf_code]
        except KeyError as err:
            raise ValueError(f"PVOG bootstrap has no leaf path for {leaf_code}") from err


def _collect_leaf_paths(
    node: PersonalMatterNode,
    *,
    root: PersonalMatterNode,
    parent: PersonalMatterNode | None,
    source_version: str | None,
    paths: dict[str, PvogSourcePath],
) -> None:
    """Collect leaf paths while preserving the existing leaf-only traversal semantics."""
    if not node._has_children:
        if node.code:
            paths[node.code] = PvogSourcePath(
                root_code=root.code,
                root_label=root.label,
                parent_code=parent.code if parent else None,
                parent_label=parent.label if parent else None,
                leaf_code=node.code,
                leaf_label=node.label,
                source_version=source_version,
            )
        return
    for child in node.children:
        _collect_leaf_paths(child, root=root, parent=node, source_version=source_version, paths=paths)


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
    _source_path: PvogSourcePath | None = PrivateAttr(default=None)

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
    def source_path(self) -> PvogSourcePath | None:
        """Return the optional bootstrap path associated with this service row."""
        return self._source_path

    def attach_source_path(self, path: PvogSourcePath) -> None:
        """Associate the bootstrap path used to discover this row."""
        self._source_path = path

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
