"""The Cloudflare Browser Run adapter: the only module that knows the bearer token and the JSON envelope."""

from __future__ import annotations

import base64
import binascii
import logging
import time
from collections.abc import Callable
from types import TracebackType

import httpx
from pydantic import JsonValue

from discovery_ingest.browser.classify import envelope, is_rate_limited, raise_for_response
from discovery_ingest.browser.consent import has_leftover_consent_widget
from discovery_ingest.browser.endpoints import Endpoint, endpoint_url
from discovery_ingest.browser.errors import BrowserRequestError, ScreenshotOversize, ScreenshotUnreadable
from discovery_ingest.browser.images import CONTENT_TYPES, image_kind
from discovery_ingest.browser.payloads import Body, content_body, snapshot_body
from discovery_ingest.browser.port import RenderedPage, ScreenshotImage
from discovery_ingest.browser.throttle import Throttle
from discovery_ingest.browser.usage import parse_ms_used
from discovery_ingest.config import BrowserSettings

MAX_SCREENSHOT_BYTES = 8 * 1024 * 1024
NEVER_SENT = (httpx.ConnectError, httpx.ConnectTimeout)
"""Transport failures before any byte reached Cloudflare: they book no browser time."""
logger = logging.getLogger(__name__)


class CloudflareBrowserClient:
    """Render pages through quick actions, one throttled call at a time."""

    def __init__(
        self,
        settings: BrowserSettings,
        *,
        user_agent: str,
        http: httpx.Client | None = None,
        throttle: Throttle | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Wire the credentials (a missing one raises :class:`ValueError`), the throttle and the HTTP client."""
        self._account_id, self._token = settings.credentials()
        self._user_agent = user_agent
        self._interval = settings.browser_min_interval_seconds
        self._timeout = settings.browser_request_timeout_seconds
        self._owns_http = http is None
        self._http = http or httpx.Client(trust_env=True)
        self._throttle = throttle or Throttle(self._interval)
        self._clock = clock

    def close(self) -> None:
        """Close the HTTP client this instance created; leave an injected client for its owner to close."""
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> CloudflareBrowserClient:
        """Return ``self`` for use as a context manager."""
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None
    ) -> None:
        """Close the owned HTTP client, whether or not the body raised."""
        self.close()

    def render(self, url: str) -> RenderedPage:
        """Return the rendered DOM of ``url`` with the target's status and final URL from ``meta``."""
        payload, ms_used = self._call("content", content_body(url, self._user_agent))
        return _rendered(payload, ms_used)

    def screenshot(self, url: str, *, consent_click: bool = True) -> ScreenshotImage:
        """Return a full-page JPEG and the DOM of the same session from one ``/snapshot`` call (tier 2 when ``consent_click``)."""
        body = snapshot_body(url, self._user_agent, ["content", "screenshot"], consent_click=consent_click)
        payload, ms_used = self._call("snapshot", body)
        return _screenshot_image(payload, ms_used, url)

    def _call(self, endpoint: Endpoint, body: Body) -> tuple[dict[str, JsonValue], int]:
        response, measured_ms = self._send(endpoint, body)
        if is_rate_limited(response, self._interval):
            response, measured_ms = self._send(endpoint, body)
        ms_used = _ms_used(response, measured_ms)
        raise_for_response(response, self._scrub, ms_used)
        return envelope(response, ms_used), ms_used

    def _send(self, endpoint: Endpoint, body: Body) -> tuple[httpx.Response, int]:
        with self._throttle:
            started = self._clock()
            try:
                response = self._http.post(
                    endpoint_url(self._account_id, endpoint),
                    json=body,
                    headers={"Authorization": f"Bearer {self._token}"},
                    timeout=self._timeout,
                )
            except httpx.HTTPError as err:
                ms_used = 0 if isinstance(err, NEVER_SENT) else _elapsed_ms(self._clock, started)
                raise BrowserRequestError(
                    self._scrub(f"{type(err).__name__}: {err}"), retryable=True, ms_used=ms_used
                ) from err
            return response, _elapsed_ms(self._clock, started)

    def _scrub(self, text: str) -> str:
        return text.replace(self._token, "<redacted>").replace(self._account_id, "<redacted>")


def _ms_used(response: httpx.Response, measured_ms: int) -> int:
    """Return the browser time Cloudflare reported for ``response``, else the measured duration of the call."""
    reported = parse_ms_used(response.headers.get("x-browser-ms-used"))
    return measured_ms if reported is None else reported


def _elapsed_ms(clock: Callable[[], float], started: float) -> int:
    return round((clock() - started) * 1000)


def _target(payload: dict[str, JsonValue]) -> tuple[int | None, str | None]:
    """Return the target's HTTP status and final URL from ``meta`` (``None`` for what the envelope left out)."""
    meta = payload.get("meta")
    fields = meta if isinstance(meta, dict) else {}
    status, final = fields.get("status"), fields.get("finalUrl")
    return status if isinstance(status, int) else None, final if isinstance(final, str) else None


def _rendered(payload: dict[str, JsonValue], ms_used: int) -> RenderedPage:
    html = payload.get("result")
    if not isinstance(html, str):
        raise BrowserRequestError("Cloudflare returned no HTML", retryable=False, ms_used=ms_used)
    return RenderedPage(html, ms_used, *_target(payload))


def _screenshot_image(payload: dict[str, JsonValue], ms_used: int, url: str) -> ScreenshotImage:
    result = payload.get("result")
    fields = result if isinstance(result, dict) else {}
    html = fields.get("content")
    html_value = html if isinstance(html, str) else None
    page = None if html_value is None else RenderedPage(html_value, ms_used, *_target(payload))
    _flag_leftover_consent_widget(html_value, url)
    data = _decode_image(fields.get("screenshot"), ms_used, page)
    return ScreenshotImage(data, CONTENT_TYPES[image_kind(data)], ms_used, html_value, *_target(payload))


def _flag_leftover_consent_widget(html: str | None, url: str) -> None:
    """Log (never raise, never block) when tiers 1-2 missed a cookie/consent widget (tier 3, D3)."""
    if html is not None and has_leftover_consent_widget(html):
        logger.warning("consent widget still present after screenshot capture", extra={"url": url})


def _decode_image(encoded: JsonValue, ms_used: int, page: RenderedPage | None) -> bytes:
    try:
        data = base64.b64decode(encoded, validate=True) if isinstance(encoded, str) else b""
    except binascii.Error:
        data = b""
    if image_kind(data) not in CONTENT_TYPES:
        raise ScreenshotUnreadable("Cloudflare returned no readable image", ms_used=ms_used, page=page)
    if len(data) > MAX_SCREENSHOT_BYTES:
        raise ScreenshotOversize(len(data), ms_used, page=page)
    return data
