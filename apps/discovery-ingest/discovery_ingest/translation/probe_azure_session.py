"""The probe's session: one engine on a recording transport, the spend reserved before each call, and the calls themselves.

A call reserves its estimated characters before it is sent, so the billed characters never pass the plan's cap. A
refusal of the service, or the cap, ends the session with :class:`ProbeStop`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, cast

import httpx

from discovery_ingest.browser.throttle import Throttle
from discovery_ingest.translation.adapters.azure_translator import AzureTranslator
from discovery_ingest.translation.adapters.azure_translator_http import AzureConnection, AzureTransport, Reply
from discovery_ingest.translation.errors import QuotaExceeded, TranslationEngineError, UnusableOutputError
from discovery_ingest.translation.findings import Finding
from discovery_ingest.translation.glossary import load_glossary
from discovery_ingest.translation.probe_azure_types import ANSWERED, AzureProbePlan, Exchange
from discovery_ingest.translation.repair import Checked, Translator, check_outcome
from discovery_ingest.translation.units import TranslationBatch, TranslationUnit

SOURCE_LOCALE: Final = "de"


class ProbeStop(Exception):
    """The probe must end: the spend cap is reached, or the service refused the calls."""


class _RecordingTransport(AzureTransport):
    """The production transport, which also keeps an :class:`Exchange` for each request it answered."""

    def __init__(self, connection: AzureConnection, throttle: Throttle, http: httpx.Client) -> None:
        """Keep the connection, the throttle and the client as the production transport does."""
        super().__init__(connection, throttle, http)
        self.exchanges: list[Exchange] = []

    def send(self, body: Mapping[str, object]) -> Reply:
        """Send ``body`` as the production transport does, and record what it sent and what was reported."""
        reply = super().send(body)
        self.exchanges.append(Exchange(_sent_characters(body), reply.metered))
        return reply


def _sent_characters(body: Mapping[str, object]) -> int:
    inputs = cast("list[dict[str, str]]", body["inputs"])
    return sum(len(item["text"]) for item in inputs)


def _billed(exchange: Exchange) -> float:
    """Return what the service billed for a request; without the header, what was sent (the adapter's own fallback)."""
    return exchange.sent if exchange.metered is None else exchange.metered


def _unusable(unit: TranslationUnit) -> Checked:
    """Return a unit whose answer was unusable: it fails, with no translation to show."""
    return Checked(unit, TranslationUnit(unit.key, "", ""), (Finding("unusable_output", "text", "no usable answer"),))


class Session:
    """One probe run's calls: the engine, its recording transport, and the spend reserved before each call."""

    def __init__(self, plan: AzureProbePlan, http: httpx.Client) -> None:
        """Build the engine on a recording transport paced by the plan's interval."""
        self.plan = plan
        self._transport = _RecordingTransport(plan.connection, Throttle(plan.min_interval_seconds), http)
        self.engine = AzureTranslator(self._transport)

    @property
    def exchanges(self) -> tuple[Exchange, ...]:
        """Every request answered so far, in order."""
        return tuple(self._transport.exchanges)

    def reserve(self, need: float) -> None:
        """Raise :class:`ProbeStop` unless ``need`` more characters fit under the cap."""
        spent = sum(_billed(exchange) for exchange in self._transport.exchanges)
        if spent + need > self.plan.max_characters:
            raise ProbeStop(f"max usage {self.plan.max_characters} reached")

    def translate(self, units: tuple[TranslationUnit, ...], locale: str, translator: Translator) -> list[Checked]:
        """Translate ``units`` into ``locale`` through ``translator`` and check each answer against its source."""
        batch = TranslationBatch(SOURCE_LOCALE, locale, units, load_glossary(locale))
        self.reserve(self.engine.estimate(batch).amount)
        try:
            return check_outcome(batch, translator.translate(batch))
        except UnusableOutputError:
            return [_unusable(unit) for unit in units]
        except TranslationEngineError as err:
            raise ProbeStop(f"{type(err).__name__}: {err}") from err

    def send(self, body: Mapping[str, object], need: int) -> Exchange:
        """Send one raw request that needs ``need`` characters and return its exchange."""
        self.reserve(need)
        try:
            self._transport.send(body)
        except TranslationEngineError as err:
            raise ProbeStop(f"{type(err).__name__}: {err}") from err
        return self._transport.exchanges[-1]

    def attempt(self, batch: TranslationBatch) -> str:
        """Translate ``batch`` once: ``ANSWERED``, or the error it returned; a spent quota ends the session."""
        try:
            self.engine.translate(batch)
        except QuotaExceeded as err:
            raise ProbeStop(f"{type(err).__name__}: {err}") from err
        except TranslationEngineError as err:
            return f"{type(err).__name__}: {err}"
        return ANSWERED
