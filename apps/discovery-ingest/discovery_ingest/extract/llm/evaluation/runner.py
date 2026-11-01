"""Run gold pages through the cleaner, the model and grounding, one page at a time under the neuron meter."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence

from pydantic import ValidationError

from discovery_ingest.extract.clean import CleanPage, clean_page
from discovery_ingest.extract.llm.client import LlmClient, LlmResult
from discovery_ingest.extract.llm.errors import LlmAuthError, LlmError, LlmInvalidOutput, LlmQuotaExceeded
from discovery_ingest.extract.llm.evaluation.cache import CacheEntry, CacheKey, ResultCache, text_digest
from discovery_ingest.extract.llm.evaluation.gold import DocumentCase, GoldPage
from discovery_ingest.extract.llm.evaluation.page import (
    DocumentContext,
    Failure,
    PageContext,
    Reply,
    StopRun,
    refusal_stop,
)
from discovery_ingest.extract.llm.evaluation.results import EvalRun, PageResult, PageStatus, Scores, Usage
from discovery_ingest.extract.llm.evaluation.scoring import (
    nothing_found,
    nothing_found_document,
    score_document,
    score_page,
)
from discovery_ingest.extract.llm.evaluation.setup import EvalSetup
from discovery_ingest.extract.llm.ground import ground
from discovery_ingest.extract.llm.ground_state import Grounded
from discovery_ingest.extract.llm.meter import NeuronMeter, Reservation
from discovery_ingest.extract.llm.prices import actual_neurons, reserved_output_tokens
from discovery_ingest.extract.llm.prompt import build_messages
from discovery_ingest.extract.llm.schema import PageExtraction, build_json_schema

_STOP_REASONS: dict[type[LlmError], str] = {LlmQuotaExceeded: "llm_quota", LlmAuthError: "llm_auth"}
"""Errors that end the run, not the page: the day is spent or the token is refused."""


def _parse(result: LlmResult) -> PageExtraction | Failure:
    try:
        return PageExtraction.model_validate_json(result.parsed_json)
    except ValidationError:
        return Failure("invalid_output", "the answer does not match the extraction schema")


class EvalRunner:
    """Send each gold page to the model once, reserve neurons first and score what grounding keeps."""

    def __init__(self, client: LlmClient, meter: NeuronMeter, setup: EvalSetup, cache: ResultCache) -> None:
        """Wire the model client, the neuron meter, the run setup and the cache of earlier answers."""
        self._client = client
        self._meter = meter
        self._setup = setup
        self._cache = cache
        self._schema = build_json_schema(setup.taxonomy)

    def run(self, pages: Sequence[GoldPage]) -> EvalRun:
        """Run ``pages`` in order; a spent budget or a quota error ends the run with the pages done so far."""
        return self._run_all(len(pages), (self._page(page) for page in pages))

    def run_documents(self, cases: Sequence[DocumentCase]) -> EvalRun:
        """Run document-level cases in order; mirrors ``run`` but scores each against its own document's text."""
        return self._run_all(len(cases), (self._document(case) for case in cases))

    def _run_all(self, total: int, results: Iterator[PageResult]) -> EvalRun:
        done: list[PageResult] = []
        stopped = None
        try:
            done.extend(results)  # extend appends one by one, so a stop keeps the results finished so far
        except StopRun as stop:
            stopped = stop.stopped
        return EvalRun(tuple(done), total, self._meter.used_neurons, stopped)

    def _page(self, gold: GoldPage) -> PageResult:
        page = PageContext(gold, clean_page(gold.html, gold.source_url, max_chars=self._setup.max_chars))
        return self._run_one(
            page.cleaned, gold.name, nothing_found(gold), page.result, page.failed, lambda e, g: score_page(gold, e, g)
        )

    def _document(self, case: DocumentCase) -> PageResult:
        cleaned = CleanPage(
            text=case.document_text, links=frozenset(), language=None, title=None, truncated=False, version="doc-gold-1"
        )
        doc = DocumentContext(case, cleaned)
        return self._run_one(
            doc.cleaned,
            doc.cache_name,
            nothing_found_document(case),
            doc.result,
            doc.failed,
            lambda _extraction, grounded: score_document(case, grounded),
        )

    def _run_one(
        self,
        cleaned: CleanPage,
        cache_name: str,
        empty: Scores,
        result: Callable[[PageStatus, Usage, Scores, str | None], PageResult],
        failed: Callable[[Failure, Usage | None], PageResult],
        score: Callable[[PageExtraction, Grounded], Scores],
    ) -> PageResult:
        """Ask (cached), parse and ground once; ``result``/``failed``/``score`` are the one thing a page and a document differ on."""
        if not cleaned.text.strip():
            return result("empty_page", Usage(), empty, None)
        reply = self._cached_or_ask(cleaned, cache_name)
        if isinstance(reply, Failure):
            return failed(reply, None)
        extraction = _parse(reply.result)
        if isinstance(extraction, Failure):
            return failed(extraction, reply.usage)
        grounded = ground(extraction, cleaned, self._setup.taxonomy)
        return result("ok", reply.usage, score(extraction, grounded), None)

    def _cached_or_ask(self, cleaned: CleanPage, cache_name: str) -> Reply | Failure:
        key = self._key(cleaned, cache_name)
        entry = self._cache.get(key)
        if entry is not None:
            usage = Usage(entry.result.input_tokens, entry.result.output_tokens, entry.neurons, cached=True)
            return Reply(entry.result, usage)
        reply = self._ask(cleaned)
        if isinstance(reply, Reply):
            self._cache.put(key, CacheEntry(reply.result, reply.usage.neurons))
        return reply

    def _key(self, cleaned: CleanPage, cache_name: str) -> CacheKey:
        setup = self._setup
        digest = text_digest(cleaned.text)
        return CacheKey(setup.model, setup.prompt_version, cleaned.version, setup.taxonomy.digest(), cache_name, digest)

    def _ask(self, cleaned: CleanPage) -> Reply | Failure:
        reservation = self._reserve(len(cleaned.text))
        try:
            result = self._client.extract(
                build_messages(cleaned, self._setup.taxonomy), self._schema, max_tokens=self._setup.max_tokens
            )
        except LlmError as err:
            return self._on_error(err)
        self._meter.settle(reservation, result)
        return Reply(result, self._usage(result, reservation))

    def _on_error(self, err: LlmError) -> Failure:
        """Stop the run for a quota or token error (telling the ledger about a spent day); fail the page otherwise."""
        if isinstance(err, LlmQuotaExceeded):
            self._meter.exhaust()
        reason = _STOP_REASONS.get(type(err))
        if reason:
            raise StopRun(reason, str(err)) from err
        return Failure("invalid_output" if isinstance(err, LlmInvalidOutput) else "request_error", str(err))

    def _reserve(self, input_chars: int) -> Reservation:
        output = reserved_output_tokens(input_chars, self._setup.max_tokens)
        answer = self._meter.reserve(self._setup.model, input_chars, output)
        if isinstance(answer, Reservation):
            return answer
        raise refusal_stop(answer, self._setup.neuron_budget, self._meter.used_neurons)

    def _usage(self, result: LlmResult, reservation: Reservation) -> Usage:
        neurons = actual_neurons(result)
        return Usage(
            result.input_tokens, result.output_tokens, float(reservation.neurons) if neurons is None else neurons
        )
