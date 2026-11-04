"""The extraction model: the JSON schema sent to the model and the validator of what comes back."""

from __future__ import annotations

import unicodedata
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints, TypeAdapter

from discovery_ingest.extract.llm.taxonomy import Taxonomy
from discovery_ingest.json_types import JsonObject, JsonSchema

MAX_NAME_LENGTH = 120
MAX_QUOTE_LENGTH = 300
MAX_CONDITION_LENGTH = 300
MAX_DOMAIN_CODES = 2
MAX_SITUATION_CODES = 3
MAX_DOCUMENTS = 40
MAX_DEPENDENCIES = 40

PageKind = Literal["service", "form", "list", "login_or_error", "other"]
Role = Literal["required", "form", "issued"]


def _reject_control_characters(value: str) -> str:
    if any(unicodedata.category(char) == "Cc" for char in value):
        raise ValueError("control character in text")
    return value


def _blank_to_none(value: str | None) -> str | None:
    return value or None


_Clean = AfterValidator(_reject_control_characters)
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_NAME_LENGTH), _Clean]
Quote = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_QUOTE_LENGTH), _Clean]
Condition = Annotated[str, StringConstraints(strip_whitespace=True, max_length=MAX_CONDITION_LENGTH), _Clean]
Url = Annotated[str, StringConstraints(strip_whitespace=True), _Clean]
Code = Url


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DocumentItem(_Strict):
    """A document, form or issued document the page names, with the quote that proves it."""

    name: Name
    role: Role
    quote: Quote
    url: Annotated[Url | None, AfterValidator(_blank_to_none)] = None
    condition: Annotated[Condition | None, AfterValidator(_blank_to_none)] = None
    is_optional: bool = False


class DependencyItem(_Strict):
    """A statement that ``parent`` requires ``requires``, by document name."""

    parent: Name
    requires: Name
    quote: Quote
    condition: Annotated[Condition | None, AfterValidator(_blank_to_none)] = None


class PageExtraction(_Strict):
    """Everything the model says about one page."""

    page_kind: PageKind
    domain_codes: list[Code] = Field(max_length=MAX_DOMAIN_CODES)
    situation_codes: list[Code] = Field(default_factory=list, max_length=MAX_SITUATION_CODES)
    documents: list[DocumentItem] = Field(max_length=MAX_DOCUMENTS)
    dependencies: list[DependencyItem] = Field(max_length=MAX_DEPENDENCIES)


def _restrict_codes(code_property: JsonObject, codes: tuple[str, ...]) -> None:
    """Offer ``codes`` as an enum; an empty vocabulary allows no codes (an empty enum is not valid JSON schema)."""
    code_property["items"] = {"type": "string", "enum": [*codes]} if codes else {"type": "string"}
    if not codes:
        code_property["maxItems"] = 0


def _property(schema: JsonObject, name: str) -> JsonObject:
    """Return the object schema of property ``name``; the generated schema always has one."""
    properties = schema["properties"]
    if not isinstance(properties, dict):
        raise ValueError("generated schema has no properties object")
    node = properties[name]
    if not isinstance(node, dict):
        raise ValueError(f"generated schema property {name} is not an object")
    return node


def build_json_schema(taxonomy: Taxonomy) -> JsonSchema:
    """Return the JSON schema for ``response_format`` with the vocabulary as code enums (a hint; grounding decides)."""
    schema = TypeAdapter(JsonSchema).validate_python(PageExtraction.model_json_schema())
    _restrict_codes(_property(schema, "domain_codes"), taxonomy.domain_codes)
    _restrict_codes(_property(schema, "situation_codes"), taxonomy.situation_codes)
    return schema
