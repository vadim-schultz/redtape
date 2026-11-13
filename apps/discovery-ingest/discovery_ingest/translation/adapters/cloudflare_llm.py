"""The Cloudflare Workers AI translator: an LLM through the existing ``LlmClient``, JSON-schema output, neuron usage.

The only translation module that imports a provider client. It registers itself as ``llm``.
"""

from __future__ import annotations

import math

from discovery_ingest.browser.throttle import Throttle
from discovery_ingest.extract.llm.client import LlmClient, LlmResult
from discovery_ingest.extract.llm.cloudflare import CloudflareAiClient
from discovery_ingest.extract.llm.errors import (
    LlmAuthError,
    LlmError,
    LlmInvalidOutput,
    LlmQuotaExceeded,
    LlmRequestError,
)
from discovery_ingest.extract.llm.prices import CHARS_PER_TOKEN, actual_neurons, estimate
from discovery_ingest.llm_settings import load_llm_settings
from discovery_ingest.translation.adapters.cloudflare_answer import parse_answer
from discovery_ingest.translation.adapters.cloudflare_prompt import LANGUAGE_NAMES, UNITS_SCHEMA, build_messages
from discovery_ingest.translation.errors import (
    PermanentError,
    QuotaExceeded,
    TransientError,
    TranslationEngineError,
    Unauthorised,
    UnusableOutputError,
)
from discovery_ingest.translation.locale_codes import DEFAULT_TARGET_LOCALES, provider_code, register_locale_map
from discovery_ingest.translation.registry import EngineConfig, register_engine
from discovery_ingest.translation.units import CallLimits, TranslationBatch, TranslationOutcome, Usage, UsageUnit

NAME = "llm"
OUTPUT_TOKENS_PER_INPUT_TOKEN = 2.0
"""Translated text is longer in tokens than the German (Cyrillic and Turkish tokenise heavily); a reservation ceiling."""
DEFAULT_MIN_INTERVAL_SECONDS = 1.0
DEFAULT_MAX_TOKENS = 4000
UNITS_PER_CALL = 50
"""The most units a claim carries, so one locale of a batch is always one prompt."""


_FIXED_CATEGORIES: tuple[tuple[type[LlmError], type[TranslationEngineError]], ...] = (
    (LlmQuotaExceeded, QuotaExceeded),
    (LlmAuthError, Unauthorised),
    (LlmInvalidOutput, UnusableOutputError),
)
"""Checked in order; every other Workers AI failure is a request error, transient or permanent by its own flag."""


def _map_error(err: LlmError) -> TranslationEngineError:
    """Map a Workers AI failure onto the port's categories; the message is already scrubbed of the credentials."""
    for llm_type, category in _FIXED_CATEGORIES:
        if isinstance(err, llm_type):
            return category(str(err))
    retryable = isinstance(err, LlmRequestError) and err.retryable
    return TransientError(str(err)) if retryable else PermanentError(str(err))


class LlmTranslator:
    """Translate batches with one Workers AI chat model, one call per batch."""

    name = NAME
    usage_unit: UsageUnit = "neurons"
    repairs = True

    def __init__(self, client: LlmClient, *, model: str, max_tokens: int) -> None:
        """Keep the client, the model id (for estimates) and the output limit of one call."""
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    @property
    def limits(self) -> CallLimits:
        """One prompt per locale of up to 50 units, one call at a time: the client paces its own requests."""
        return CallLimits(UNITS_PER_CALL, 1)

    def translate(self, batch: TranslationBatch) -> TranslationOutcome:
        """Return one result per unit in order and the neurons the call cost."""
        language = LANGUAGE_NAMES.get(provider_code(NAME, batch.target_locale), batch.target_locale)
        result = self._call(batch, language)
        results = parse_answer(result.parsed_json, batch.units)
        return TranslationOutcome(results, self._usage(result, batch), result.model)

    def estimate(self, batch: TranslationBatch) -> Usage:
        """Return the neurons to reserve: the units in, about twice their tokens out, capped at the output limit."""
        input_chars = _input_chars(batch)
        output = min(self._max_tokens, math.ceil(input_chars / CHARS_PER_TOKEN * OUTPUT_TOKENS_PER_INPUT_TOKEN))
        return Usage("neurons", float(estimate(self._model, input_chars, output)))

    def _call(self, batch: TranslationBatch, language: str) -> LlmResult:
        try:
            return self._client.extract(build_messages(batch, language), UNITS_SCHEMA, max_tokens=self._max_tokens)
        except LlmError as err:
            raise _map_error(err) from err

    def _usage(self, result: LlmResult, batch: TranslationBatch) -> Usage:
        actual = actual_neurons(result)
        return self.estimate(batch) if actual is None else Usage("neurons", actual)


def _input_chars(batch: TranslationBatch) -> int:
    units = sum(len(u.title) + len(u.description) + len(u.context) for u in batch.units)
    glossary = sum(len(e.source) + len(e.rendering) for e in batch.glossary.terms)
    return units + glossary


def _build(config: EngineConfig) -> LlmTranslator:
    settings = load_llm_settings()
    interval = DEFAULT_MIN_INTERVAL_SECONDS if config.min_interval_seconds is None else config.min_interval_seconds
    model = config.model or settings.llm_model
    client = CloudflareAiClient(settings, model=model, http=config.http, throttle=Throttle(interval))
    return LlmTranslator(client, model=model, max_tokens=min(settings.llm_max_tokens, DEFAULT_MAX_TOKENS))


register_locale_map(NAME, {code: code for code in DEFAULT_TARGET_LOCALES})
register_engine(NAME, _build)
