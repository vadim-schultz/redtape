"""The gold set: hand-labelled pages, each ``<name>.html`` with its ``<name>.gold.json``."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, JsonValue, ValidationError

from discovery_ingest.extract.decode import decode_html
from discovery_ingest.extract.llm.schema import Code, Name, PageKind, Role

GOLD_SUFFIX = ".gold.json"


class GoldError(Exception):
    """The gold set cannot be read: a missing directory, page or a label outside the schema."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GoldDocument(_Strict):
    """A document a reader finds on the page; ``condition`` and ``is_optional`` document the label, scoring ignores them."""

    name: Name
    role: Role
    condition: str | None = None
    is_optional: bool = False


class GoldDependency(_Strict):
    """A statement of the page that ``parent`` requires ``requires``."""

    parent: Name
    requires: Name


class GoldPage(_Strict):
    """One labelled page with its decoded html; ``source_url`` is the base the cleaner resolves links against."""

    name: str
    html: str
    source_url: str
    page_kind: PageKind
    documents: tuple[GoldDocument, ...]
    dependencies: tuple[GoldDependency, ...]
    domain_codes: tuple[Code, ...]
    situation_codes: tuple[Code, ...]


def _labels(directory: Path, name: str) -> dict[str, JsonValue]:
    try:
        labels = json.loads((directory / f"{name}{GOLD_SUFFIX}").read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise GoldError(f"{name}: unreadable labels: {err}") from err
    if not isinstance(labels, dict):
        raise GoldError(f"{name}: the labels must be a JSON object")
    return labels


def _read(directory: Path, name: str) -> GoldPage:
    html_path = directory / f"{name}.html"
    if not html_path.is_file():
        raise GoldError(f"{name}: no {html_path.name} beside the gold labels")
    html = decode_html(html_path.read_bytes(), None)
    try:
        return GoldPage.model_validate({**_labels(directory, name), "name": name, "html": html})
    except ValidationError as err:
        raise GoldError(f"{name}: {err}") from err


def load_gold(directory: Path, *, limit: int | None = None) -> list[GoldPage]:
    """Return the labelled pages of ``directory`` in name order, the first ``limit`` of them when given."""
    if not directory.is_dir():
        raise GoldError(f"gold set not found: {directory} is not a directory")
    names = sorted(path.name.removesuffix(GOLD_SUFFIX) for path in directory.glob(f"*{GOLD_SUFFIX}"))
    return [_read(directory, name) for name in names[:limit]]
