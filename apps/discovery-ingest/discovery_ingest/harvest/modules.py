"""xZufi modules of a PVOG payload and the table that says which ones hold documents."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import NamedTuple

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from discovery_ingest.harvest.text import collapse, list_items, paragraph_lines
from discovery_ingest.mentions import MentionRole


class Link(BaseModel):
    """One link of a module; either part may be missing in the payload."""

    model_config = ConfigDict(extra="ignore")

    title: str | None = None
    uri: str | None = None


class Module(BaseModel):
    """The fields of one xZufi module that the harvester reads."""

    model_config = ConfigDict(extra="ignore")

    code: str = ""
    text: str | None = None
    filled: bool = False
    links: list[Link] = []

    @field_validator("links", mode="before")
    @classmethod
    def _keep_link_objects(cls, value: object) -> list[object]:
        return [entry for entry in value if isinstance(entry, dict)] if isinstance(value, list) else []


class Found(NamedTuple):
    """A document name a strategy found in a module, with the URL of its own when it has one."""

    title: str
    official_url: str | None = None


Strategy = Callable[[Module], list[Found]]


@dataclass(frozen=True, slots=True)
class ModuleSelector:
    """The role a module's items play and how to split the module into items."""

    role: MentionRole
    strategy: Strategy


def _text_items(module: Module) -> list[Found]:
    html = module.text or ""
    return [Found(item) for item in list_items(html) or paragraph_lines(html)]


def _link_items(module: Module) -> list[Found]:
    return [Found(collapse(link.title), link.uri.strip()) for link in module.links if link.title and link.uri]


MODULE_SELECTORS: dict[str, ModuleSelector] = {
    "08": ModuleSelector("required", _text_items),  # Erforderliche Unterlagen
    "14": ModuleSelector("form", _link_items),  # Formulare
}


def _parse_module(entry: dict[str, object]) -> Module | None:
    try:
        return Module.model_validate(entry)
    except ValidationError:
        return None


def selected_modules(raw_payload: dict[str, object]) -> list[Module]:
    """Return the filled modules of ``raw_payload.details`` that ``MODULE_SELECTORS`` names."""
    details = raw_payload.get("details")
    entries = [entry for entry in details if isinstance(entry, dict)] if isinstance(details, list) else []
    modules = [module for entry in entries if (module := _parse_module(entry)) is not None]
    return [module for module in modules if module.filled and module.code in MODULE_SELECTORS]
