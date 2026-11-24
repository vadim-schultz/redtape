"""The Azure AI Translator engine: units into one target locale per call, billed in characters.

It registers itself as ``azure-translator``; it is not the default, and ``TRANSLATION_ENGINE`` selects it. The request
and answer shapes live in ``azure_translator_wire`` and the HTTP in ``azure_translator_http``; this module holds neither.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from discovery_ingest.translation.adapters.azure_translator_http import (
    CHARACTERS_PER_MINUTE,
    AzureConnection,
    AzureTransport,
    CharacterWindow,
)
from discovery_ingest.translation.adapters.azure_translator_wire import (
    Piece,
    characters_of,
    chunks_of,
    pieces_of,
    read_answers,
    request_body,
)
from discovery_ingest.translation.azure_settings import load_azure_translator_settings
from discovery_ingest.translation.errors import PermanentError
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


@dataclass(frozen=True, slots=True)
class _Chunk:
    """The translations of one request, in input order, and the characters the service billed for it."""

    texts: tuple[str, ...]
    billed: float


_PageKey = tuple[str, str, tuple[str, ...]]
"""A page's identity while it is translated: its source and target locales and the texts sent, in order."""


class AzureTranslator:
    """Translate batches with Azure AI Translator: one target per call, billed in the characters reported.

    A page's answered chunks are kept in a memo until the page is complete, so a retry of the page sends only the chunks
    that were not answered: an answered chunk is billed once.
    """

    name = NAME
    usage_unit: UsageUnit = "characters"
    repairs = False

    def __init__(self, transport: AzureTransport) -> None:
        """Keep the transport that sends the requests, and an empty memo of the pages not yet complete."""
        self._transport = transport
        self._memo: dict[_PageKey, list[_Chunk]] = {}

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
        """Send the requests not yet answered, in order; return the translations in input order and the characters billed."""
        key: _PageKey = (source, target, tuple(piece.text for piece in pieces))
        parts = self._memo.setdefault(key, [])
        for request in _requests_of(pieces)[len(parts) :]:
            parts.append(self._chunk(source, target, request))
        del self._memo[key]
        return [text for part in parts for text in part.texts], sum(part.billed for part in parts)

    def _chunk(self, source: str, target: str, request: Sequence[Piece]) -> _Chunk:
        """Send one request and read its answers; the billed figure is the header's, or the source characters without one."""
        sent = characters_of(request)
        reply = self._transport.send(request_body(request, source, target))
        texts = read_answers(reply.body, request, target)
        return _Chunk(tuple(texts), sent if reply.metered is None else reply.metered)


def _requests_of(pieces: Sequence[Piece]) -> list[list[Piece]]:
    """Cut ``pieces`` into requests that the limiter admits: the wire's chunks, each split again at the window's characters."""
    return [part for chunk in chunks_of(pieces) for part in _split(chunk)]


def _split(chunk: Sequence[Piece]) -> list[list[Piece]]:
    """Split ``chunk``, in order, into parts of at most ``CHARACTERS_PER_MINUTE``; a single text over that is refused."""
    parts: list[list[Piece]] = []
    for piece in chunk:
        if len(piece.text) > CHARACTERS_PER_MINUTE:
            raise PermanentError("a text is longer than the characters a minute allow; nothing was sent")
        if parts and characters_of(parts[-1]) + len(piece.text) <= CHARACTERS_PER_MINUTE:
            parts[-1].append(piece)
        else:
            parts.append([piece])
    return parts


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
    return AzureTranslator(AzureTransport(connection, CharacterWindow(min_gap_seconds=interval), config.http))


register_locale_map(NAME, {code: code for code in DEFAULT_TARGET_LOCALES})
register_engine(NAME, _build)
