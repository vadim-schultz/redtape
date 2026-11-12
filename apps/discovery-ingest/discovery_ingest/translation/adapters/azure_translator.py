"""The Azure AI Translator engine: units into one target locale per call, billed in characters.

It registers itself as ``azure-translator``; it is not the default, and ``TRANSLATION_ENGINE`` selects it. The request
and answer shapes live in ``azure_translator_wire`` and the HTTP in ``azure_translator_http``; this module holds neither.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from discovery_ingest.browser.throttle import Throttle
from discovery_ingest.translation.adapters.azure_translator_http import AzureConnection, AzureTransport
from discovery_ingest.translation.adapters.azure_translator_wire import (
    Piece,
    characters_of,
    chunks_of,
    pieces_of,
    read_answers,
    request_body,
)
from discovery_ingest.translation.azure_settings import load_azure_translator_settings
from discovery_ingest.translation.locale_codes import DEFAULT_TARGET_LOCALES, provider_code, register_locale_map
from discovery_ingest.translation.registry import EngineConfig, register_engine
from discovery_ingest.translation.units import (
    CallLimits,
    TranslationBatch,
    TranslationOutcome,
    TranslationUnit,
    Usage,
    UsageUnit,
)

NAME: Final = "azure-translator"
UNITS_PER_CALL: Final = 50
"""The most units a claim carries; the wire module cuts the inputs of a call again to the request limits."""
DEFAULT_MIN_INTERVAL_SECONDS: Final = 1.0


class AzureTranslator:
    """Translate batches with Azure AI Translator: one target per call, billed in the characters reported."""

    name = NAME
    usage_unit: UsageUnit = "characters"
    repairs = False

    def __init__(self, transport: AzureTransport) -> None:
        """Keep the transport that sends the requests."""
        self._transport = transport

    @property
    def limits(self) -> CallLimits:
        """Up to 50 units a call, one call at a time: the transport paces the requests."""
        return CallLimits(UNITS_PER_CALL, 1)

    def translate(self, batch: TranslationBatch) -> TranslationOutcome:
        """Return one result per unit in order and the characters the service billed for its requests."""
        code = provider_code(NAME, batch.target_locale)
        pieces = pieces_of(batch.units)
        texts, billed = self._translated(batch.source_locale, code, pieces)
        return TranslationOutcome(assemble(batch.units, pieces, texts), Usage(self.usage_unit, billed), None)

    def estimate(self, batch: TranslationBatch) -> Usage:
        """Return the source characters that would be sent, which is what the service bills for plain text."""
        return Usage(self.usage_unit, float(characters_of(pieces_of(batch.units))))

    def _translated(self, source: str, target: str, pieces: Sequence[Piece]) -> tuple[list[str], float]:
        """Send each request in order; return the translations in input order and the characters billed for them."""
        texts: list[str] = []
        billed = 0.0
        for chunk in chunks_of(pieces):
            reply = self._transport.send(request_body(chunk, source, target))
            texts.extend(read_answers(reply.body, chunk, target))
            billed += characters_of(chunk) if reply.metered is None else reply.metered
        return texts, billed


def assemble(
    units: Sequence[TranslationUnit], pieces: Sequence[Piece], texts: Sequence[str]
) -> tuple[TranslationUnit, ...]:
    """Put each translated text back into its unit, in the order of the units; a field that was not sent stays blank."""
    found = {(piece.unit, piece.field): text for piece, text in zip(pieces, texts, strict=True)}
    return tuple(
        TranslationUnit(unit.key, found.get((number, "title"), ""), found.get((number, "description"), ""))
        for number, unit in enumerate(units)
    )


def _build(config: EngineConfig) -> AzureTranslator:
    """Build the engine from the Azure settings; refuse to start, naming any unset key or region variable."""
    settings = load_azure_translator_settings()
    key, region = settings.credentials()
    connection = AzureConnection(settings.azure_translator_endpoint, settings.azure_translator_api_version, key, region)
    interval = DEFAULT_MIN_INTERVAL_SECONDS if config.min_interval_seconds is None else config.min_interval_seconds
    return AzureTranslator(AzureTransport(connection, Throttle(interval), config.http))


register_locale_map(NAME, {code: code for code in DEFAULT_TARGET_LOCALES})
register_engine(NAME, _build)
