"""Probe items 5 and 7: the quality of the answer and the cleaner against toMarkdown."""

from __future__ import annotations

import httpx
from pydantic import JsonValue, ValidationError

from discovery_ingest.extract.clean import CleanPage
from discovery_ingest.extract.llm.envelope import read_result
from discovery_ingest.extract.llm.errors import LlmInvalidOutput
from discovery_ingest.extract.llm.ground import ground
from discovery_ingest.extract.llm.probe_calls import RawCall
from discovery_ingest.extract.llm.probe_report import ProbeRow
from discovery_ingest.extract.llm.probe_shape import failure_text, fields
from discovery_ingest.extract.llm.schema import PageExtraction
from discovery_ingest.extract.llm.taxonomy import Taxonomy

CHARS_PER_TOKEN = 3


def _grounded_text(extraction: PageExtraction, clean_page: CleanPage, taxonomy: Taxonomy) -> str:
    grounded, seen = ground(extraction, clean_page, taxonomy), extraction
    diagnostics = grounded.diagnostics
    documents = f"grounded documents {len(grounded.documents)} of {len(seen.documents)}"
    dependencies = f"dependencies {len(grounded.dependencies)} of {len(seen.dependencies)}"
    drops = f"dropped={dict(diagnostics.dropped)}; unknown_codes={diagnostics.unknown_codes}"
    return f"page_kind={diagnostics.page_kind}; {documents}; {dependencies}; {drops}"


def _parse(model: str, response: httpx.Response) -> PageExtraction | str:
    """Return the parsed ``PageExtraction`` or the reason it could not be parsed."""
    try:
        return PageExtraction.model_validate_json(read_result(response, model).parsed_json)
    except LlmInvalidOutput as err:
        return f"answer unusable: {err}"
    except ValidationError as err:
        first = err.errors()[0]
        return f"PageExtraction invalid: {err.error_count()} errors; first {first['type']} at {first['loc']}"


def quality_row(model: str, call: RawCall, clean_page: CleanPage, taxonomy: Taxonomy) -> ProbeRow:
    """Parse the answer as a ``PageExtraction`` and ground it, so the eval has a first look."""
    if call.response is None or not call.ok:
        return ProbeRow(model, "quality", "skipped: no answer to parse")
    parsed = _parse(model, call.response)
    finding = parsed if isinstance(parsed, str) else _grounded_text(parsed, clean_page, taxonomy)
    return ProbeRow(model, "quality", finding)


def _converted(call: RawCall) -> dict[str, JsonValue]:
    """Return the first converted file of a toMarkdown answer (empty when the call failed or the shape is off)."""
    payload = call.payload if call.ok else None
    result = payload.get("result") if payload else None
    return fields(result[0]) if isinstance(result, list) and result else {}


def cleaner_row(clean_page: CleanPage, call: RawCall) -> ProbeRow:
    """Compare the in-house cleaner with Workers AI ``toMarkdown`` on the same HTML, or say it is not supported."""
    base = f"cleaner {len(clean_page.text)} chars (~{len(clean_page.text) // CHARS_PER_TOKEN} tokens)"
    entry = _converted(call)
    data = entry.get("data")
    if not isinstance(data, str):
        reason = failure_text(call) if not call.ok else "no converted text in the result"
        return ProbeRow(None, "cleaner", f"{base}; toMarkdown not supported: {reason}")
    shown = f"toMarkdown {len(data)} chars (~{len(data) // CHARS_PER_TOKEN} tokens, tokens={entry.get('tokens')})"
    return ProbeRow(None, "cleaner", f"{base}; {shown}")
