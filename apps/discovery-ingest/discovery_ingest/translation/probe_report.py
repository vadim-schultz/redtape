"""The ``translate probe`` report: a typed model, printed as one JSON object."""

from __future__ import annotations

from pydantic import BaseModel, Field

from discovery_ingest.translation.units import UsageUnit

MAX_FAILED_LISTED = 20


class FailedUnit(BaseModel):
    """A sampled unit that did not pass: its key and the checks it failed (``unusable_output`` when nothing came back)."""

    key: str
    checks: list[str]


class ProbeReport(BaseModel):
    """What the probe learned about one engine on one locale; ``stopped`` says why it ended early (else ``None``)."""

    engine: str
    model: str | None = None
    locale: str
    sample_size: int
    translated: int = 0
    validated_ok: int = 0
    unusable_units: int = 0
    pass_rate: float = 0.0
    failures: dict[str, int] = Field(default_factory=dict)
    failed: list[FailedUnit] = Field(default_factory=list)
    usage_unit: UsageUnit
    usage_total: float = 0.0
    usage_per_unit: float | None = None
    batches: int = 0
    latency_ms_per_batch: int | None = None
    corpus_total: int = 0
    target_locales: int = 0
    projected_usage_locale: float | None = None
    projected_usage_all_locales: float | None = None
    daily_budget: float | None = None
    days_at_daily_budget: float | None = None
    sheet: str | None = None
    stopped: str | None = None
