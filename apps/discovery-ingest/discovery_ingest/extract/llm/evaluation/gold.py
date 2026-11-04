"""The gold set: hand-labelled pages, each ``<name>.html`` with its ``<name>.gold.json``."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict, JsonValue, ValidationError, model_validator

from discovery_ingest.extract.decode import decode_html
from discovery_ingest.extract.llm.schema import Code, Name, PageKind, Role
from discovery_ingest.extract.llm.taxonomy import Taxonomy
from discovery_ingest.pvog.category_mapping import categories_for_legacy_codes

GOLD_SUFFIX = ".gold.json"


class GoldError(Exception):
    """The gold set cannot be read: a missing directory, page or a label outside the schema."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GoldDocument(_Strict):
    """A document a reader finds on the page; ``condition`` and ``is_optional`` document the label, scoring ignores them.

    ``document_text`` is the document's own text (its own title and purpose line, not an excerpt of the page that
    names it); absent for most of the 47 gold documents, hand-authored for the small subset chapter 5 scores.
    """

    name: Name
    role: Role
    condition: str | None = None
    is_optional: bool = False
    document_text: str | None = None


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
    category_codes: tuple[Code, ...]

    @model_validator(mode="before")
    @classmethod
    def _translate_legacy_axes(cls, value: object) -> object:
        """Translate old gold labels through the frozen crosswalk."""
        if not isinstance(value, dict) or "category_codes" in value:
            return value
        domains = categories_for_legacy_codes("domain", tuple(value.get("domain_codes") or ()))
        situations = categories_for_legacy_codes("life_situation", tuple(value.get("situation_codes") or ()))
        return {
            **{key: item for key, item in value.items() if key not in {"domain_codes", "situation_codes"}},
            "category_codes": tuple(dict.fromkeys((*domains, *situations))),
        }


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


class DocumentCase(_Strict):
    """One gold document scored against its own text.

    The gold label is the page's situation codes: production copies a page's codes onto every document it
    mentions (X8), so that is the one gold label a document has today.
    """

    page_name: str
    document_name: str
    document_text: str
    gold_category_codes: tuple[Code, ...]


def document_cases(pages: Sequence[GoldPage]) -> list[DocumentCase]:
    """Return one `DocumentCase` per gold document that carries its own `document_text`; the rest are simply absent."""
    return [
        DocumentCase(
            page_name=page.name,
            document_name=document.name,
            document_text=document.document_text,
            gold_category_codes=page.category_codes,
        )
        for page in pages
        for document in page.documents
        if document.document_text is not None
    ]


def unknown_codes(page: GoldPage, taxonomy: Taxonomy) -> list[str]:
    """Return the category codes of ``page`` that the vocabulary does not contain."""
    return [code for code in page.category_codes if code not in taxonomy.category_codes]
