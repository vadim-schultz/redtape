"""The probe's rows and the printable table; every line is scrubbed of the credentials."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from discovery_ingest.config import BrowserSettings

REDACTED = "<redacted>"


@dataclass(frozen=True, slots=True)
class ProbeRow:
    """One call's outcome: status (``None`` when nothing answered), browser and measured milliseconds, shape."""

    variant: str
    target: str
    status: int | None
    ms_used: int | None
    measured_ms: int
    shape: str
    details: tuple[str, ...] = ()

    @property
    def cost_ms(self) -> int:
        """Browser milliseconds this call is booked at: the header, else the measured duration."""
        return self.measured_ms if self.ms_used is None else self.ms_used


@dataclass(slots=True)
class ProbeReport:
    """Every row, the response header names seen and why the probe stopped early (``refused``: Cloudflare said no)."""

    rows: list[ProbeRow] = field(default_factory=list)
    header_names: set[str] = field(default_factory=set)
    stopped: str | None = None
    refused: bool = False

    @property
    def total_ms(self) -> int:
        """Browser milliseconds spent across all rows."""
        return sum(row.cost_ms for row in self.rows)


def _secrets(settings: BrowserSettings) -> list[str]:
    token = settings.cloudflare_browser_api_token
    values = [settings.cloudflare_account_id, token.get_secret_value() if token else None]
    return [value for value in values if value]


def _scrub(text: str, secrets: list[str]) -> str:
    for secret in secrets:
        text = text.replace(secret, REDACTED)
    return text


def _row_line(row: ProbeRow) -> str:
    ms = f"ms={row.ms_used}" if row.ms_used is not None else f"ms=absent(measured {row.measured_ms})"
    return " | ".join([row.variant, row.target, f"status={row.status}", ms, row.shape, "; ".join(row.details)])


def _lines(report: ProbeReport) -> Iterator[str]:
    yield "variant | target | status | browser ms | shape | details"
    yield from (_row_line(row) for row in report.rows)
    yield f"response headers seen: {', '.join(sorted(report.header_names))}"
    yield f"calls={len(report.rows)} browser_ms_total={report.total_ms} (~{report.total_ms / 1000:.1f} s of 600 s a day)"
    if report.stopped:
        yield f"stopped: {report.stopped}"


def report_lines(report: ProbeReport, settings: BrowserSettings) -> list[str]:
    """Return the table, one line per call, with the token and the account id replaced by ``<redacted>``."""
    secrets = _secrets(settings)
    return [_scrub(line, secrets) for line in _lines(report)]
