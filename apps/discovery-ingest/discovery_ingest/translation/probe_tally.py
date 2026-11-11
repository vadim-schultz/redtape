"""What the probe has seen so far: results, findings, usage and latency, and the report they add up to."""

from __future__ import annotations

from collections import Counter

from discovery_ingest.translation.findings import Finding
from discovery_ingest.translation.probe_report import MAX_FAILED_LISTED, FailedUnit, ProbeReport
from discovery_ingest.translation.probe_sheet import SheetRow
from discovery_ingest.translation.units import TranslationUnit, Usage, UsageUnit

UNUSABLE = "unusable_output"


def _rows(source: TranslationUnit, translated: TranslationUnit | None, findings: list[Finding]) -> list[SheetRow]:
    """Return the title row and the description row of one unit; a failed field lists the checks that found it."""
    pairs = (
        ("title", source.title, translated.title if translated else ""),
        ("description", source.description, translated.description if translated else ""),
    )
    return [
        SheetRow(source.key, name, german, text, ", ".join(f.check for f in findings if f.field == name))
        for name, german, text in pairs
    ]


class ProbeTally:
    """Collect the outcome of each batch; :meth:`report` turns the totals into a :class:`ProbeReport`."""

    def __init__(self, unit: UsageUnit) -> None:
        """Start empty for an engine billed in ``unit``."""
        self._unit: UsageUnit = unit
        self.rows: list[SheetRow] = []
        self.failed: list[FailedUnit] = []
        self.failures: Counter[str] = Counter()
        self.usage = Usage(unit, 0.0)
        self.translated = 0
        self.ok = 0
        self.unusable = 0
        self.batches = 0
        self.latencies_ms: list[int] = []
        self.model: str | None = None

    @property
    def attempted(self) -> int:
        """Units whose batch was answered, usably or not."""
        return self.translated + self.unusable

    def add_result(self, source: TranslationUnit, translated: TranslationUnit, findings: list[Finding]) -> None:
        """Record one translated unit with the findings of its validation."""
        self.translated += 1
        self.rows.extend(_rows(source, translated, findings))
        if not findings:
            self.ok += 1
            return
        checks = sorted({finding.check for finding in findings})
        self.failures.update(checks)
        self.failed.append(FailedUnit(key=source.key, checks=checks))

    def add_unusable(self, source: TranslationUnit) -> None:
        """Record a unit whose batch came back unusable: it failed, with no translation to show."""
        self.unusable += 1
        self.failures.update([UNUSABLE])
        self.failed.append(FailedUnit(key=source.key, checks=[UNUSABLE]))
        self.rows.extend(_rows(source, None, [Finding(UNUSABLE, "title", ""), Finding(UNUSABLE, "description", "")]))

    def add_batch(self, usage: Usage, latency_ms: int, model: str | None) -> None:
        """Record the usage, latency and model of one answered batch."""
        self.batches += 1
        self.usage = self.usage.plus(usage)
        self.latencies_ms.append(latency_ms)
        self.model = model or self.model

    def report(self, engine: str, locale: str, sample_size: int) -> ProbeReport:
        """Return the report of what was recorded; projections are added by the caller."""
        latency = round(sum(self.latencies_ms) / len(self.latencies_ms)) if self.latencies_ms else None
        return ProbeReport(
            engine=engine,
            model=self.model,
            locale=locale,
            sample_size=sample_size,
            translated=self.translated,
            validated_ok=self.ok,
            unusable_units=self.unusable,
            pass_rate=round(self.ok / self.attempted, 4) if self.attempted else 0.0,
            failures=dict(self.failures),
            failed=self.failed[:MAX_FAILED_LISTED],
            usage_unit=self._unit,
            usage_total=self.usage.amount,
            usage_per_unit=self.usage.amount / self.translated if self.translated else None,
            batches=self.batches,
            latency_ms_per_batch=latency,
        )
