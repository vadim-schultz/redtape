"""``translate probe``: read the public candidate list, translate a fixed sample, write the sheet and render the report."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import httpx

from discovery_ingest.operations.probes import ProbeOutcome
from discovery_ingest.translation.glossary import load_glossary
from discovery_ingest.translation.locale_codes import DEFAULT_TARGET_LOCALES
from discovery_ingest.translation.probe import ProbeOptions, run_probe
from discovery_ingest.translation.probe_sample import PublicCandidateReader
from discovery_ingest.translation.probe_sheet import write_sheet
from discovery_ingest.translation.registry import EngineConfig, build_engine

PROBE_MIN_INTERVAL_SECONDS = 1.0
BATCH_SIZE = 5
SHEET_DIR = Path("translation-probe")


@dataclass(frozen=True, slots=True)
class TranslateProbeRequest:
    """What the operator asked for: engine, locale, sample size, caps and where the sheet goes."""

    engine: str
    locale: str
    sample: int
    model: str | None
    sheet: Path | None
    max_usage: float
    daily_budget: float


def _options(request: TranslateProbeRequest) -> ProbeOptions:
    return ProbeOptions(
        locale=request.locale,
        glossary=load_glossary(request.locale),
        sample=request.sample,
        batch_size=BATCH_SIZE,
        max_usage=request.max_usage,
        daily_budget=request.daily_budget,
        target_count=len(DEFAULT_TARGET_LOCALES),
    )


def translate_probe(request: TranslateProbeRequest, api_url: str) -> ProbeOutcome:
    """Run the probe over real HTTP and render the report as one JSON text (the adapters keep credentials out of errors).

    The outcome fails when the probe stopped early. Nothing is written to the database; the sheet is the only file.
    """
    with httpx.Client(trust_env=True) as http:
        config = EngineConfig(model=request.model, http=http, min_interval_seconds=PROBE_MIN_INTERVAL_SECONDS)
        corpus = PublicCandidateReader(api_url, http).read()
        engine = build_engine(request.engine, config)
        result = run_probe(engine, corpus, _options(request))
    path = request.sheet or SHEET_DIR / f"{request.engine}-{request.locale}.csv"
    result.report.sheet = str(write_sheet(result.rows, path))
    return ProbeOutcome([result.report.model_dump_json(indent=2)], result.report.stopped is not None)
