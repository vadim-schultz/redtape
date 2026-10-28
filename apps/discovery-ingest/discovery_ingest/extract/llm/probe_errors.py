"""Probe items 3 and 6: what each error response means (acceptance, the schema violation, the daily quota)."""

from __future__ import annotations

from collections.abc import Sequence

import httpx

from discovery_ingest.extract.llm.classify import error_for
from discovery_ingest.extract.llm.envelope import read_result
from discovery_ingest.extract.llm.errors import (
    LlmAuthError,
    LlmError,
    LlmInvalidOutput,
    LlmQuotaExceeded,
    LlmRequestError,
)
from discovery_ingest.extract.llm.probe_calls import RawCall
from discovery_ingest.extract.llm.probe_report import ProbeRow
from discovery_ingest.extract.llm.probe_shape import failure_text

QUOTA_NOT_PROVOKED = "not provoked; record the first natural occurrence (status and body) in the ledger"


def _error(call: RawCall) -> LlmError | None:
    if call.response is None or call.ok:
        return None
    return error_for(call.response, lambda text: text)


def _acceptance(error: LlmError) -> str:
    if isinstance(error, LlmInvalidOutput):
        return f"accepts response_format but JSON mode failed: {error}"
    if isinstance(error, LlmRequestError) and not error.retryable:
        return f"does not accept response_format: {error}"
    return f"inconclusive ({type(error).__name__}): {error}"


def acceptance_row(model: str, call: RawCall) -> ProbeRow:
    """Say whether the model accepted ``response_format``; a rejection is a finding, not a crash."""
    error = _error(call)
    if call.response is None:
        return ProbeRow(model, "acceptance", f"no answer: {failure_text(call)}")
    return ProbeRow(model, "acceptance", "accepts response_format (HTTP 200)" if error is None else _acceptance(error))


def _violation(response: httpx.Response, call: RawCall, model: str) -> str:
    error = _error(call)
    if error is not None:
        return f"{type(error).__name__}: {error}"
    try:
        read_result(response, model)
    except LlmInvalidOutput as err:
        return f"answered 200 but the answer is unusable: {err}"
    return "answered 200 with an answer that parses as JSON despite the tiny max_tokens"


def violation_row(model: str, call: RawCall | None) -> ProbeRow:
    """Report what a deliberately truncated answer (``max_tokens`` 16) does: the JSON-mode error or an invalid body."""
    if call is None:
        return ProbeRow(model, "violation", "skipped: response_format was not accepted")
    if call.response is None:
        return ProbeRow(model, "violation", f"no answer: {failure_text(call)}")
    return ProbeRow(model, "violation", _violation(call.response, call, model))


def quota_row(model: str, calls: Sequence[RawCall]) -> ProbeRow:
    """Record a daily-allowance error seen on any call of the model; the probe never provokes one."""
    for call in calls:
        error = _error(call)
        if isinstance(error, LlmQuotaExceeded):
            return ProbeRow(model, "quota", f"recorded: {type(error).__name__}: {error}")
    return ProbeRow(model, "quota", QUOTA_NOT_PROVOKED)


def refusal(call: RawCall) -> str | None:
    """Return why the probe must stop (a rejected token or the daily quota), or ``None``."""
    error = _error(call)
    if isinstance(error, LlmAuthError | LlmQuotaExceeded):
        return f"{type(error).__name__} ({error}); no further calls were made"
    return None
