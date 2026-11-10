"""Run the ``embed probe``: native dimension, reduced dimensions and the batch ladder, stopping at the first rejection."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from discovery_ingest.extract.embedding.client import EmbeddingResult
from discovery_ingest.extract.embedding.probe_report import BatchCheck, DimensionCheck, EmbedProbeReport
from discovery_ingest.extract.llm.errors import LlmError, LlmRequestError

REDUCED_DIMENSIONS = (768, 512, 256, 128)
BATCH_LADDER = (1, 8, 16, 32, 64, 100, 128, 256)
SAMPLE_TEXTS = (
    "Antrag auf Kindergeld bei der Familienkasse",
    "Anmeldung einer Wohnung beim Einwohnermeldeamt",
    "Bescheinigung über die Rentenversicherung beantragen",
    "Gewerbeanmeldung für Einzelunternehmer",
    "Wohngeld: Antrag auf Mietzuschuss",
)


class Embedder(Protocol):
    """What the probe needs from the client."""

    def embed(self, texts: Sequence[str], *, dimensions: int | None = None) -> EmbeddingResult:
        """Return the vectors of ``texts``, reduced to ``dimensions`` when given."""
        ...


@dataclass(frozen=True, slots=True)
class Rejection:
    """The provider refused this input (a non-retryable ``4xx``): a finding about its limits, not a failure."""

    reason: str


def sample_texts(count: int) -> list[str]:
    """Return ``count`` German sample texts, cycling through the fixed set."""
    return [SAMPLE_TEXTS[index % len(SAMPLE_TEXTS)] for index in range(count)]


def _attempt(embedder: Embedder, count: int, dimensions: int | None = None) -> EmbeddingResult | Rejection:
    """Embed ``count`` samples; a plain rejection is returned, every other :class:`LlmError` propagates."""
    try:
        return embedder.embed(sample_texts(count), dimensions=dimensions)
    except LlmRequestError as err:
        if err.retryable:
            raise
        return Rejection(str(err))


def _probe_native(embedder: Embedder, report: EmbedProbeReport) -> int | None:
    """Embed one text; return the native dimension, or ``None`` after recording why the probe cannot go on."""
    outcome = _attempt(embedder, 1)
    if isinstance(outcome, Rejection):
        report.stopped = f"the first call was rejected: {outcome.reason}"
        return None
    report.dimension, report.latency_ms = outcome.dimension, outcome.latency_ms
    report.add_usage(outcome)
    return outcome.dimension


def _dimension_check(requested: int, outcome: EmbeddingResult | Rejection) -> DimensionCheck:
    if isinstance(outcome, Rejection):
        return DimensionCheck(requested=requested, returned=None, accepted=False, reason=outcome.reason)
    return DimensionCheck(requested=requested, returned=outcome.dimension, accepted=outcome.dimension == requested)


def _probe_dimensions(embedder: Embedder, report: EmbedProbeReport, native: int) -> None:
    for requested in (dim for dim in REDUCED_DIMENSIONS if dim < native):
        outcome = _attempt(embedder, 1, requested)
        report.dimension_checks.append(_dimension_check(requested, outcome))
        if isinstance(outcome, EmbeddingResult):
            report.add_usage(outcome)


def _probe_batches(embedder: Embedder, report: EmbedProbeReport) -> None:
    for size in BATCH_LADDER:
        outcome = _attempt(embedder, size)
        if isinstance(outcome, Rejection):
            report.batch_checks.append(BatchCheck(size=size, accepted=False, reason=outcome.reason))
            return
        report.batch_checks.append(BatchCheck(size=size, accepted=True, latency_ms=outcome.latency_ms))
        report.add_usage(outcome)


def run_embed_probe(embedder: Embedder, model: str) -> EmbedProbeReport:
    """Probe ``model`` through ``embedder``; an auth, quota or transient error ends the probe with ``stopped`` set."""
    report = EmbedProbeReport(model=model)
    try:
        native = _probe_native(embedder, report)
        if native is not None:
            _probe_dimensions(embedder, report, native)
            _probe_batches(embedder, report)
    except LlmError as err:
        report.stopped = f"{type(err).__name__}: {err}"
    return report
