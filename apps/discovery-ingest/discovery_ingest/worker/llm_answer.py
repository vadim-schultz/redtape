"""What the model call of llm_extract makes of an answer: a parsed extraction or a reason it is unusable."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from discovery_ingest.extract.llm.client import ChatMessage, LlmResult
from discovery_ingest.extract.llm.meter import Denied, LedgerUnavailable
from discovery_ingest.extract.llm.schema import PageExtraction

Messages = list[ChatMessage]
REPAIR_HINT: ChatMessage = {
    "role": "user",
    "content": "Your previous answer was not valid JSON for the schema. Answer again with only the JSON object.",
}


@dataclass(frozen=True, slots=True)
class Invalid:
    """An answer that is no usable extraction; the call may still have been billed."""

    reason: str


def parse_answer(result: LlmResult) -> PageExtraction | Invalid:
    """Return the extraction in ``result``, or :class:`Invalid` when it does not fit the schema."""
    try:
        return PageExtraction.model_validate_json(result.parsed_json)
    except ValidationError:
        return Invalid("the answer does not match the extraction schema")


def denial_reason(answer: Denied | LedgerUnavailable) -> str:
    """Say in words why a reservation was refused."""
    if isinstance(answer, Denied):
        return "the run's neuron budget is reached" if answer.reason == "run_budget" else "the day's neurons are spent"
    return "the neuron ledger is unavailable"
