"""The probe's rows and the printable tables; every line is scrubbed of the credentials."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from discovery_ingest.llm_settings import LlmSettings

REDACTED = "<redacted>"


@dataclass(frozen=True, slots=True)
class ProbeRow:
    """One finding: the probe ``item`` it answers and what was seen; ``model`` is ``None`` for run-wide findings."""

    model: str | None
    item: str
    finding: str


@dataclass(slots=True)
class ProbeReport:
    """Every row, the neurons the probe computed it spent and why it stopped early (``refused``: Cloudflare said no)."""

    rows: list[ProbeRow] = field(default_factory=list)
    neurons_spent: float = 0.0
    stopped: str | None = None
    refused: bool = False

    def models(self) -> list[str]:
        """The probed models in first-seen order."""
        return list(dict.fromkeys(row.model for row in self.rows if row.model is not None))


def _table(title: str, rows: list[ProbeRow]) -> Iterator[str]:
    yield title
    yield "| item | finding |"
    yield from (f"| {row.item} | {row.finding} |" for row in rows)
    yield ""


def _lines(report: ProbeReport) -> Iterator[str]:
    for model in report.models():
        yield from _table(f"model {model}", [row for row in report.rows if row.model == model])
    shared = [row for row in report.rows if row.model is None]
    if shared:
        yield from _table("run-wide", shared)
    yield f"neurons_spent={report.neurons_spent:.1f} (computed from the price table; compare the dashboard)"
    if report.stopped:
        yield f"stopped: {report.stopped}"


def _scrub(text: str, secrets: list[str]) -> str:
    for secret in secrets:
        text = text.replace(secret, REDACTED)
    return text


def report_lines(report: ProbeReport, settings: LlmSettings) -> list[str]:
    """Return the tables, with the token and the account id replaced by ``<redacted>``."""
    token = settings.cloudflare_ai_api_token
    secrets = [
        value for value in (settings.cloudflare_account_id, token.get_secret_value() if token else None) if value
    ]
    return [_scrub(line, secrets) for line in _lines(report)]
