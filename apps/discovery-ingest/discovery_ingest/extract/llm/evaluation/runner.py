"""Run gold pages through the cleaner, the model and grounding, one page at a time under the neuron meter."""

from __future__ import annotations

from collections.abc import Iterator, Sequence

from pydantic import ValidationError

from discovery_ingest.extract.clean import CleanPage, clean_page
from discovery_ingest.extract.llm.client import LlmClient, LlmResult
from discovery_ingest.extract.llm.errors import LlmInvalidOutput, LlmRequestError
from discovery_ingest.extract.llm.evaluation.gold import GoldPage
from discovery_ingest.extract.llm.evaluation.page import Failure, PageContext, Reply, StopRun
from discovery_ingest.extract.llm.evaluation.results import EvalRun, PageResult, Usage
from discovery_ingest.extract.llm.evaluation.scoring import nothing_found, score_page
from discovery_ingest.extract.llm.evaluation.setup import EvalSetup
from discovery_ingest.extract.llm.ground import ground
from discovery_ingest.extract.llm.meter import NeuronMeter, Reservation
from discovery_ingest.extract.llm.prices import cost
from discovery_ingest.extract.llm.prompt import build_messages
from discovery_ingest.extract.llm.schema import PageExtraction, build_json_schema


def _parse(result: LlmResult) -> PageExtraction | Failure:
    try:
        return PageExtraction.model_validate_json(result.parsed_json)
    except ValidationError:
        return Failure("invalid_output", "the answer does not match the extraction schema")


class EvalRunner:
    """Send each gold page to the model once, reserve neurons first and score what grounding keeps."""

    def __init__(self, client: LlmClient, meter: NeuronMeter, setup: EvalSetup) -> None:
        """Wire the model client, the neuron meter and the run setup."""
        self._client = client
        self._meter = meter
        self._setup = setup
        self._schema = build_json_schema(setup.taxonomy)

    def run(self, pages: Sequence[GoldPage]) -> EvalRun:
        """Run ``pages`` in order; a spent budget or a quota error ends the run with the pages done so far."""
        done: list[PageResult] = []
        stopped = None
        try:
            done.extend(self._results(pages))  # extend appends page by page, so a stop keeps the finished pages
        except StopRun as stop:
            stopped = stop.stopped
        return EvalRun(tuple(done), len(pages), self._meter.used_neurons, stopped)

    def _results(self, pages: Sequence[GoldPage]) -> Iterator[PageResult]:
        for page in pages:
            yield self._page(page)

    def _page(self, gold: GoldPage) -> PageResult:
        page = PageContext(gold, clean_page(gold.html, gold.source_url, max_chars=self._setup.max_chars))
        if not page.cleaned.text.strip():
            return page.result("empty_page", Usage(), nothing_found(gold))
        reply = self._ask(page.cleaned)
        if isinstance(reply, Failure):
            return page.failed(reply)
        extraction = _parse(reply.result)
        if isinstance(extraction, Failure):
            return page.failed(extraction, reply.usage)
        grounded = ground(extraction, page.cleaned, self._setup.taxonomy)
        return page.result("ok", reply.usage, score_page(gold, extraction, grounded))

    def _ask(self, cleaned: CleanPage) -> Reply | Failure:
        reservation = self._reserve(len(cleaned.text))
        try:
            result = self._client.extract(
                build_messages(cleaned, self._setup.taxonomy), self._schema, max_tokens=self._setup.max_tokens
            )
        except LlmInvalidOutput as err:
            return Failure("invalid_output", str(err))
        except LlmRequestError as err:
            return Failure("request_error", str(err))
        self._meter.settle(reservation, result)
        return Reply(result, self._usage(result, reservation))

    def _reserve(self, input_chars: int) -> Reservation:
        answer = self._meter.reserve(self._setup.model, input_chars, self._setup.max_tokens)
        if isinstance(answer, Reservation):
            return answer
        raise StopRun("stopped", "the run stopped before the last page")

    def _usage(self, result: LlmResult, reservation: Reservation) -> Usage:
        if result.input_tokens is None or result.output_tokens is None:
            return Usage(result.input_tokens, result.output_tokens, float(reservation.neurons))
        neurons = cost(self._setup.model, result.input_tokens, result.output_tokens)
        return Usage(result.input_tokens, result.output_tokens, neurons)
