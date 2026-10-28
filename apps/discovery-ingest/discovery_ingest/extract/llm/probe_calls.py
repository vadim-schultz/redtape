"""The probe's raw HTTP: one throttled POST that keeps the whole response, because the probe reads what the client hides."""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx
from pydantic import JsonValue

from discovery_ingest.browser.throttle import Throttle
from discovery_ingest.extract.llm.classify import json_payload
from discovery_ingest.extract.llm.endpoints import Endpoint, endpoint_url
from discovery_ingest.extract.llm.payloads import Body
from discovery_ingest.llm_settings import LlmSettings


@dataclass(frozen=True, slots=True)
class RawCall:
    """One answered request (``response``) or one that got no answer (``error``), with its wall time."""

    response: httpx.Response | None
    error: str | None
    wall_ms: int

    @property
    def status(self) -> int | None:
        """The HTTP status, or ``None`` when nothing answered."""
        return self.response.status_code if self.response is not None else None

    @property
    def ok(self) -> bool:
        """Whether the call got a 2xx answer."""
        return self.status is not None and self.status < 400

    @property
    def payload(self) -> dict[str, JsonValue] | None:
        """The body as a JSON object, or ``None``."""
        return json_payload(self.response) if self.response is not None else None


class ProbeClient:
    """Send probe requests with the bearer token, one at a time, spaced by the throttle."""

    def __init__(self, settings: LlmSettings, http: httpx.Client, throttle: Throttle) -> None:
        """Read the credentials (a missing one raises :class:`ValueError`) and keep the transport."""
        self._account_id, self._token = settings.ai_credentials()
        self._timeout = settings.llm_request_timeout_seconds
        self._http, self._throttle = http, throttle

    def post(self, endpoint: Endpoint, body: Body, model: str = "") -> RawCall:
        """POST a JSON ``body`` to ``endpoint`` (``model`` fills the ``run`` path)."""
        return self._send(endpoint_url(self._account_id, endpoint, model), json=body)

    def markdown(self, html: str) -> RawCall:
        """POST ``html`` to the toMarkdown endpoint as a multipart file."""
        files = {"files": ("page.html", html.encode(), "text/html")}
        return self._send(endpoint_url(self._account_id, "tomarkdown"), files=files)

    def _send(
        self, url: str, *, json: Body | None = None, files: dict[str, tuple[str, bytes, str]] | None = None
    ) -> RawCall:
        started = time.monotonic()
        with self._throttle:
            try:
                response = self._http.post(
                    url,
                    json=json,
                    files=files,
                    headers={"Authorization": f"Bearer {self._token}"},
                    timeout=self._timeout,
                )
            except httpx.HTTPError as err:
                return RawCall(None, f"{type(err).__name__}: {err}", round((time.monotonic() - started) * 1000))
        return RawCall(response, None, round((time.monotonic() - started) * 1000))
