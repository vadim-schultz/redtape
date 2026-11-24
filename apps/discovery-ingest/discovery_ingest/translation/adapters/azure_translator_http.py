"""The Azure Translator transport: a sliding character window and a retry for throttled requests, then one POST.

The window holds the characters sent in any 60 s at or below the free tier's per-minute budget, with a minimum gap between
calls. A throttled request waits (its ``Retry-After``, else 2 s then 4 s) and is sent again, at most twice, before the
port error is raised. The key travels only in the subscription header and is removed from every error text.
"""

from __future__ import annotations

import time
import uuid
from collections import deque
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Final, cast

import httpx

from discovery_ingest.translation.adapters.azure_translator_errors import (
    is_rate_limited,
    port_error,
    redacted,
    retry_after_of,
)
from discovery_ingest.translation.errors import PermanentError, TransientError, UnusableOutputError

USAGE_HEADER: Final = "X-metered-usage"
"""The response header that carries the characters the service billed for one request."""
CHARACTERS_PER_MINUTE: Final = 28_000
"""What the window admits in 60 s; the free tier enforces 33,300, and the headroom absorbs requests in flight."""
WINDOW_SECONDS: Final = 60.0
MAX_RETRIES: Final = 2
"""Sends after the first one for a throttled request; the third answer is the one that is raised."""
BACKOFF_SECONDS: Final = (2.0, 4.0)
"""The wait before each retry when the service sent no ``Retry-After``."""
_EPSILON: Final = 1e-6
"""Added to a wait so that the entry it waits for has really left the window when the clock reads it again."""


@dataclass(frozen=True, slots=True)
class AzureConnection:
    """Where the Translator is and how it is called: the endpoint, the API version, the key and the resource region."""

    endpoint: str
    api_version: str
    key: str
    region: str


@dataclass(frozen=True, slots=True)
class Reply:
    """The JSON body of a successful request, and the characters it billed (``None`` when the header is absent)."""

    body: object
    metered: float | None


class CharacterWindow:
    """Hold the characters sent in any 60 s window at or below ``limit``, with ``min_gap_seconds`` between two calls.

    Entering :meth:`admit` waits until the call fits: the sends that are 60 s old have left the window, and the gap has
    passed since the previous call ended. A send counts from the moment its call starts.
    """

    def __init__(
        self,
        *,
        limit: int = CHARACTERS_PER_MINUTE,
        min_gap_seconds: float = 1.0,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        """Set the limit and the gap; ``clock`` and ``sleep`` default to :func:`time.monotonic` and :func:`time.sleep`."""
        self._limit = limit
        self._min_gap = min_gap_seconds
        self._clock = clock or time.monotonic
        self._sleep = sleep or time.sleep
        self._sent: deque[tuple[float, int]] = deque()
        self._last_end: float | None = None

    @contextmanager
    def admit(self, characters: int) -> Iterator[None]:
        """Wait until ``characters`` fit in the window, then run the call in the block; a call above the limit is refused."""
        if characters > self._limit:
            raise PermanentError("a request above the per-minute character limit is never sent")
        self._wait_until_admitted(characters)
        self._sent.append((self._clock(), characters))
        try:
            yield
        finally:
            self._last_end = self._clock()

    def _wait_until_admitted(self, characters: int) -> None:
        while (wait := self._wait_seconds(characters)) > 0:
            self._sleep(wait)

    def _wait_seconds(self, characters: int) -> float:
        now = self._clock()
        self._expire(now)
        return max(self._gap_left(now), self._window_left(now, characters))

    def _expire(self, now: float) -> None:
        while self._sent and now - self._sent[0][0] >= WINDOW_SECONDS:
            self._sent.popleft()

    def _gap_left(self, now: float) -> float:
        return 0.0 if self._last_end is None else self._last_end + self._min_gap - now

    def _window_left(self, now: float, characters: int) -> float:
        held = sum(chars for _, chars in self._sent)
        if not self._sent or held + characters <= self._limit:
            return 0.0
        return self._sent[0][0] + WINDOW_SECONDS - now + _EPSILON


class AzureTransport:
    """Send one translate request at a time and return its answer, or raise the port error of the failure."""

    def __init__(
        self,
        connection: AzureConnection,
        limiter: CharacterWindow,
        http: httpx.Client | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        """Keep the connection and the limiter that spaces the calls; without a client, one that reads the proxy settings.

        ``sleep`` (default :func:`time.sleep`) waits before a retry.
        """
        self._connection = connection
        self._limiter = limiter
        self._http = http if http is not None else httpx.Client(trust_env=True)
        self._sleep = sleep or time.sleep

    def send(self, body: Mapping[str, object]) -> Reply:
        """POST ``body``; return the answer and the billed characters, or raise a port error with the key removed."""
        response = self._post(body, _characters_of(body))
        if not response.is_success:
            raise port_error(response, self._connection.key)
        return Reply(_json_of(response), _metered(response))

    def _post(self, body: Mapping[str, object], characters: int, attempt: int = 0) -> httpx.Response:
        """Send ``body``; a throttled answer waits and is sent again, at most ``MAX_RETRIES`` times, then the answer stands."""
        response = self._paced(body, characters)
        if attempt == MAX_RETRIES or not is_rate_limited(response):
            return response
        self._sleep(_pause_seconds(response, attempt))
        return self._post(body, characters, attempt + 1)

    def _paced(self, body: Mapping[str, object], characters: int) -> httpx.Response:
        with self._limiter.admit(characters):
            return self._request(body)

    def _request(self, body: Mapping[str, object]) -> httpx.Response:
        try:
            return self._http.post(self._url(), params=self._params(), json=body, headers=self._headers())
        except httpx.TransportError as err:
            raise TransientError(redacted(f"Azure Translator did not answer: {err}", self._connection.key)) from err

    def _url(self) -> str:
        return f"{self._connection.endpoint.rstrip('/')}/translate"

    def _params(self) -> dict[str, str]:
        return {"api-version": self._connection.api_version}

    def _headers(self) -> dict[str, str]:
        return {
            "Ocp-Apim-Subscription-Key": self._connection.key,
            "Ocp-Apim-Subscription-Region": self._connection.region,
            "Content-Type": "application/json",
            "X-ClientTraceId": str(uuid.uuid4()),
        }


def _characters_of(body: Mapping[str, object]) -> int:
    """Return the source characters a translate request carries: the length of each input's text."""
    inputs = cast("list[dict[str, str]]", body["inputs"])
    return sum(len(item["text"]) for item in inputs)


def _pause_seconds(response: httpx.Response, attempt: int) -> float:
    """Return the wait before the next send: the service's ``Retry-After`` when it named one, else the backoff of this attempt."""
    retry_after = retry_after_of(response)
    return BACKOFF_SECONDS[attempt] if retry_after is None else retry_after


def _json_of(response: httpx.Response) -> object:
    try:
        body: object = response.json()
    except ValueError as err:
        raise UnusableOutputError("the Azure answer is not JSON") from err
    return body


def _metered(response: httpx.Response) -> float | None:
    raw = response.headers.get(USAGE_HEADER)
    try:
        return None if raw is None else float(raw)
    except ValueError:
        return None
