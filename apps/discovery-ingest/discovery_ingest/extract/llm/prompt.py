"""The versioned extraction prompt: one function per message and the stamp recorded with every result."""

from __future__ import annotations

from collections.abc import Iterable

from discovery_ingest.extract.clean import CleanPage
from discovery_ingest.extract.llm.client import ChatMessage
from discovery_ingest.extract.llm.prompt_template import PAGE_CLOSE, PAGE_OPEN, system_text
from discovery_ingest.extract.llm.taxonomy import Taxonomy, TaxonomyTerm

PROMPT_VERSION = "ext-6"


def _term_line(term: TaxonomyTerm) -> str:
    name_de, name_en = term.name_i18n.get("de", ""), term.name_i18n.get("en", "")
    description = term.description_i18n.get("en") or term.description_i18n.get("de", "")
    return f"- {term.code} | {name_de} | {name_en} | {description}"


def _section(title: str, terms: Iterable[TaxonomyTerm]) -> str:
    return "\n".join([f"{title} (code | German | English | description):", *map(_term_line, terms)])


def system_message() -> ChatMessage:
    """Return the system message: task, rules and the untrusted-content rule."""
    return {"role": "system", "content": system_text()}


def user_message(clean_page: CleanPage, taxonomy: Taxonomy) -> ChatMessage:
    """Return the user message: the vocabulary and the cleaned page text."""
    vocabulary = _section("Canonical categories", taxonomy.active_categories)
    return {"role": "user", "content": f"{vocabulary}\n\n{PAGE_OPEN}\n{clean_page.text}\n{PAGE_CLOSE}"}


def build_messages(clean_page: CleanPage, taxonomy: Taxonomy) -> list[ChatMessage]:
    """Return the chat messages that ask the model to extract ``clean_page``."""
    return [system_message(), user_message(clean_page, taxonomy)]


def extractor_version(clean_page: CleanPage, taxonomy: Taxonomy) -> str:
    """Return ``<prompt>+<cleaner>+tax:<digest>``, which changes when any of the three changes."""
    return f"{PROMPT_VERSION}+{clean_page.version}+tax:{taxonomy.digest()}"
