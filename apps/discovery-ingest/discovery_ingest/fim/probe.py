"""Probe FIM steckbrief keys: report status and top-level JSON keys, never the body."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass

from discovery_ingest.fim.keys import steckbrief_url
from discovery_ingest.worker.fetcher import FetchOutcome, PoliteUrlFetcher

SCHLUESSEL_FIELD = "leistungsschluessel"
GATE_NUMERATOR, GATE_DENOMINATOR = 4, 5


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """What one steckbrief key answered: a one-line ``detail`` and whether it confirms the key."""

    key: str
    detail: str
    confirmed: bool = False

    @property
    def line(self) -> str:
        """Return the printable report line."""
        return f"{self.key} {self.detail}"


def _top_level_keys(body: bytes | None) -> list[str] | None:
    try:
        parsed = json.loads((body or b"").decode())
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return list(parsed) if isinstance(parsed, dict) else None


def _unanswered(key: str, outcome: FetchOutcome) -> ProbeResult:
    if outcome.failure is None and outcome.http_status is not None:
        return ProbeResult(key, f"status={outcome.http_status}")
    return ProbeResult(key, f"no response: {outcome.failure or outcome.failure_message}")


def _answered(key: str, status: int | None, body: bytes | None) -> ProbeResult:
    fields = _top_level_keys(body)
    if fields is None:
        return ProbeResult(key, f"status={status} body is not a JSON object")
    return ProbeResult(
        key, f"status={status} keys={','.join(fields)}", confirmed=status == 200 and SCHLUESSEL_FIELD in fields
    )


def _result_for(key: str, outcome: FetchOutcome) -> ProbeResult:
    if outcome.failed:
        return _unanswered(key, outcome)
    return _answered(key, outcome.http_status, outcome.body)


def probe_keys(fetcher: PoliteUrlFetcher, base_url: str, keys: Sequence[str]) -> list[ProbeResult]:
    """GET the steckbrief of every key through ``fetcher``; one failing key never stops the rest."""
    return [_result_for(key, fetcher.get(steckbrief_url(base_url, key))) for key in keys]


def _confirmed_count(results: Sequence[ProbeResult]) -> int:
    return sum(result.confirmed for result in results)


def gate_passed(results: Sequence[ProbeResult]) -> bool:
    """Return whether at least four of every five keys came back 200 with a ``leistungsschluessel``."""
    return _confirmed_count(results) * GATE_DENOMINATOR >= len(results) * GATE_NUMERATOR


def probe_lines(results: Sequence[ProbeResult]) -> list[str]:
    """Return one line per key plus the decision-gate summary."""
    verdict = "passed" if gate_passed(results) else "failed"
    summary = f"gate: {_confirmed_count(results)}/{len(results)} returned 200 with {SCHLUESSEL_FIELD} ({verdict})"
    return [*(result.line for result in results), summary]
