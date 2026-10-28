"""The model call of llm_extract: reserve neurons, call, settle, parse, with one repair attempt for unusable output."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from discovery_ingest.extract.clean import CleanPage
from discovery_ingest.extract.llm.client import LlmResult
from discovery_ingest.extract.llm.errors import (
    LlmAuthError,
    LlmError,
    LlmInvalidOutput,
    LlmQuotaExceeded,
    LlmRequestError,
)
from discovery_ingest.extract.llm.meter import Denied, LedgerUnavailable, NeuronMeter, Reservation
from discovery_ingest.extract.llm.prompt import build_messages
from discovery_ingest.extract.llm.schema import PageExtraction, build_json_schema
from discovery_ingest.worker.browser_steps import Job, Settled
from discovery_ingest.worker.llm_runtime import LlmResources
from discovery_ingest.worker.settle import fail_permanently, fail_with
from discovery_ingest.worker.stop import StopDrain

Messages = list[dict[str, str]]
REPAIR_HINT = {
    "role": "user",
    "content": "Your previous answer was not valid JSON for the schema. Answer again with only the JSON object.",
}


@dataclass(frozen=True, slots=True)
class _Invalid:
    """An answer that is no usable extraction; the call may still have been billed."""

    reason: str


def _parse(result: LlmResult) -> PageExtraction | _Invalid:
    try:
        return PageExtraction.model_validate_json(result.parsed_json)
    except ValidationError:
        return _Invalid("the answer does not match the extraction schema")


def _denial(answer: Denied | LedgerUnavailable) -> str:
    if isinstance(answer, Denied):
        return "the run's neuron budget is spent" if answer.reason == "run_budget" else "the day's neurons are spent"
    return "the neuron ledger is unavailable"


class ModelCaller:
    """Ask the model about a cleaned page under the neuron meter; every limit becomes a :class:`StopDrain`."""

    def __init__(self, resources: LlmResources, meter: NeuronMeter) -> None:
        """Keep the model resources and the meter every call reserves from."""
        self._resources = resources
        self._meter = meter
        self._schema = build_json_schema(resources.taxonomy)
        self.calls = 0

    def extract(self, job: Job, cleaned: CleanPage) -> PageExtraction:
        """Return the model's extraction; settle the task as failed after a second unusable answer."""
        messages = build_messages(cleaned, self._resources.taxonomy)
        first = self._attempt(job, cleaned, messages)
        if not isinstance(first, _Invalid):
            return first
        second = self._attempt(job, cleaned, [*messages, REPAIR_HINT])
        if not isinstance(second, _Invalid):
            return second
        error = f"model {self._resources.model} returned unusable output twice: {second.reason}"
        raise Settled(fail_permanently(job.client, job.task.id, error))

    def _attempt(self, job: Job, cleaned: CleanPage, messages: Messages) -> PageExtraction | _Invalid:
        reservation = self._reserve(len(cleaned.text))
        self.calls += 1
        try:
            result = self._resources.client.extract(messages, self._schema, max_tokens=self._resources.max_tokens)
        except LlmError as err:
            return self._refused(job, reservation, err)
        self._meter.settle(reservation, result)
        return _parse(result)

    def _reserve(self, input_chars: int) -> Reservation:
        resources = self._resources
        answer = self._meter.reserve(resources.model, input_chars, resources.max_tokens)
        if isinstance(answer, LedgerUnavailable):
            self._meter.stop_using_ledger()
            answer = self._meter.reserve(resources.model, input_chars, resources.max_tokens)
        if isinstance(answer, Reservation):
            return answer
        raise StopDrain("llm_budget", _denial(answer))

    def _refused(self, job: Job, reservation: Reservation, err: LlmError) -> _Invalid:
        """Map a failed call: unusable output may be repaired, a limit stops the drain, a request error fails the task."""
        match err:
            case LlmInvalidOutput():
                return _Invalid(str(err))
            case LlmQuotaExceeded():
                raise self._quota_stop(reservation, err) from err
            case LlmAuthError():
                raise self._auth_stop(reservation, err) from err
            case LlmRequestError():
                raise Settled(fail_with(job.client, job.task.id, str(err), retryable=err.retryable)) from err
            case _:
                raise err

    def _quota_stop(self, reservation: Reservation, err: LlmQuotaExceeded) -> StopDrain:
        self._meter.refund(reservation)
        self._meter.exhaust()
        return StopDrain("llm_quota", str(err))

    def _auth_stop(self, reservation: Reservation, err: LlmAuthError) -> StopDrain:
        self._meter.refund(reservation)
        return StopDrain("error", f"Cloudflare rejected the Workers AI credentials: {err}")
