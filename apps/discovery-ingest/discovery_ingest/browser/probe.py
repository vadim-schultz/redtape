"""Send the probe plan to Cloudflare, one throttled call at a time, and stop when Cloudflare refuses."""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import replace

import httpx

from discovery_ingest.browser.endpoints import endpoint_url
from discovery_ingest.browser.probe_plan import INLINE_TARGET, ProbeCall
from discovery_ingest.browser.probe_report import ProbeReport, ProbeRow
from discovery_ingest.browser.probe_shape import describe
from discovery_ingest.browser.throttle import Throttle
from discovery_ingest.browser.usage import parse_ms_used
from discovery_ingest.config import BrowserSettings

__all__ = ["ProbeReport", "run_probe"]

REFUSALS = frozenset({401, 403, 429})
PlainSize = Callable[[str], int | None]


def _header_notes(response: httpx.Response, ms_used: int | None) -> list[str]:
    raw_ms, retry = response.headers.get("x-browser-ms-used"), response.headers.get("retry-after")
    return [
        *([f"ms_header={raw_ms!r}"] if raw_ms is not None and ms_used is None else []),
        *([f"retry-after={retry}"] if retry else []),
    ]


def _answered(call: ProbeCall, response: httpx.Response, measured_ms: int) -> ProbeRow:
    shape, details = describe(response, call.expect)
    ms_used = parse_ms_used(response.headers.get("x-browser-ms-used"))
    notes = (*details, *_header_notes(response, ms_used))
    return ProbeRow(call.variant, call.target, response.status_code, ms_used, measured_ms, shape, notes)


def _unanswered(call: ProbeCall, err: httpx.HTTPError, measured_ms: int) -> ProbeRow:
    return ProbeRow(
        call.variant, call.target, None, None, measured_ms, "no response", (f"{type(err).__name__}: {err}",)
    )


def _send(call: ProbeCall, settings: BrowserSettings, http: httpx.Client) -> httpx.Response:
    account_id, token = settings.credentials()
    return http.post(
        endpoint_url(account_id, call.endpoint),
        json=call.body,
        headers={"Authorization": f"Bearer {token}"},
        timeout=settings.browser_request_timeout_seconds,
    )


def _elapsed_ms(started: float) -> int:
    return round((time.monotonic() - started) * 1000)


def _post(call: ProbeCall, settings: BrowserSettings, http: httpx.Client) -> tuple[ProbeRow, httpx.Headers | None]:
    started = time.monotonic()
    try:
        response = _send(call, settings, http)
    except httpx.HTTPError as err:
        return _unanswered(call, err, _elapsed_ms(started)), None
    return _answered(call, response, _elapsed_ms(started)), response.headers


def _with_plain_size(row: ProbeRow, plain_size: PlainSize | None) -> ProbeRow:
    if plain_size is None or row.variant != "content" or row.target == INLINE_TARGET:
        return row
    size = plain_size(row.target)
    note = f"plain_fetch={size} B" if size is not None else "plain_fetch=unavailable"
    return replace(row, details=(*row.details, note))


def run_probe(
    settings: BrowserSettings,
    calls: Sequence[ProbeCall],
    *,
    http: httpx.Client,
    throttle: Throttle,
    max_ms: int,
    plain_size: PlainSize | None = None,
) -> ProbeReport:
    """Run ``calls`` in order; stop at the first 401, 403 or 429 and once ``max_ms`` browser milliseconds are spent."""
    report = ProbeReport()
    for call in calls:
        if report.total_ms >= max_ms:
            report.stopped = f"browser time cap of {max_ms} ms reached"
            break
        with throttle:
            row, headers = _post(call, settings, http)
        report.rows.append(_with_plain_size(row, plain_size))
        report.header_names.update(name.lower() for name in headers or ())
        if row.status in REFUSALS:
            report.stopped = f"HTTP {row.status} from Cloudflare; no further calls were made"
            report.refused = True
            break
    return report
