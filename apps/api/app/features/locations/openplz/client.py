"""Fetch and validate OpenPLZ pages.

`OpenPLZClient` wraps the public OpenPLZ API: plain sync `urllib` HTTP (no new
dependency), a fixed-interval rate limiter, and one Pydantic model per
endpoint so callers never see raw JSON.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator, Mapping
from typing import TypeVar

from pydantic import BaseModel, JsonValue, ValidationError

from app.features.locations.openplz.models import (
    OpenPLZDistrict,
    OpenPLZFederalState,
    OpenPLZLocality,
    OpenPLZMunicipality,
)

ModelT = TypeVar("ModelT", bound=BaseModel)

_QueryParams = Mapping[str, str | int]


class OpenPLZHTTPError(RuntimeError):
    """Raised when an OpenPLZ HTTP request returns a non-2xx status."""

    def __init__(self, status: int, body: str, url: str) -> None:
        """Capture the failed request's status, truncated body and url."""
        super().__init__(f"OpenPLZ request failed: status={status} url={url} body={body[:500]}")
        self.status = status
        self.body = body
        self.url = url


class OpenPLZPayloadError(RuntimeError):
    """Raised when a paged OpenPLZ response has an unexpected shape."""

    def __init__(self, endpoint: str, page: int, detail: str) -> None:
        """Capture which endpoint and page produced the malformed payload."""
        super().__init__(f"OpenPLZ paged payload error: endpoint={endpoint} page={page} detail={detail}")
        self.endpoint = endpoint
        self.page = page
        self.detail = detail


class _RateLimiter:
    """Simple fixed-interval rate limiter (sync)."""

    def __init__(self, rps: float) -> None:
        if rps <= 0:
            raise ValueError("rps must be > 0")
        self._min_interval_s = 1.0 / rps
        self._last_ts = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_ts
        if elapsed < self._min_interval_s:
            time.sleep(self._min_interval_s - elapsed)
        self._last_ts = time.monotonic()


class OpenPLZClient:
    """Minimal OpenPLZ client for import jobs.

    Uses sync urllib so we don't add new HTTP dependencies.
    """

    def __init__(
        self,
        *,
        base_url: str = "https://openplzapi.org",
        language: str = "de",
        rate_limit_rps: float = 10.0,
        timeout_s: float = 30.0,
        user_agent: str = "redtape-openplz-import/1.0",
    ) -> None:
        """Configure the upstream host, language and rate limit."""
        self._base_url = base_url.rstrip("/")
        self._language = language.strip("/")
        self._timeout_s = timeout_s
        self._headers = {
            "Accept": "application/json",
            "User-Agent": user_agent,
        }
        self._limiter = _RateLimiter(rate_limit_rps)

    def federal_states(self) -> list[OpenPLZFederalState]:
        """Fetch every OpenPLZ federal state."""
        payload = self._get_json("FederalStates")
        items = self._extract_items(payload, endpoint="FederalStates", page=1)
        return self._validate_items(items, OpenPLZFederalState, endpoint="FederalStates", page=1)

    def districts(self, state_code: str) -> Iterator[OpenPLZDistrict]:
        """Iterate every district of a federal state."""
        return self._paged(f"FederalStates/{state_code}/Districts", OpenPLZDistrict)

    def municipalities(self, district_code: str) -> Iterator[OpenPLZMunicipality]:
        """Iterate every municipality of a district."""
        return self._paged(f"Districts/{district_code}/Municipalities", OpenPLZMunicipality)

    def localities(self, district_code: str) -> Iterator[OpenPLZLocality]:
        """Iterate every postal-code locality of a district."""
        return self._paged(f"Districts/{district_code}/Localities", OpenPLZLocality)

    def _paged(
        self,
        endpoint: str,
        model: type[ModelT],
        *,
        page_size: int = 50,
        max_pages: int | None = 10_000,
    ) -> Iterator[ModelT]:
        """Iterate every item of a paged OpenPLZ endpoint, validated against `model`.

        Paging query params are `page` and `pageSize` (per OpenPLZ docs). An
        empty page ends iteration; `max_pages` is a hard stop regardless.
        """
        page = 1
        while True:
            payload = self._get_json(endpoint, {"page": page, "pageSize": page_size})
            items = self._extract_items(payload, endpoint=endpoint, page=page)
            if not items:
                return
            yield from self._validate_items(items, model, endpoint=endpoint, page=page)

            page += 1
            if max_pages is not None and page > max_pages:
                return

    def _extract_items(self, payload: JsonValue, *, endpoint: str, page: int) -> list[JsonValue]:
        """Extract the list of raw items from a paged response payload.

        A list is the page itself; an object uses its `items` key, else
        `data`; anything else is a malformed page.
        """
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            items = payload.get("items")
            if isinstance(items, list):
                return items
            data = payload.get("data")
            if isinstance(data, list):
                return data
            raise OpenPLZPayloadError(endpoint, page, f"unexpected paged payload shape: keys={list(payload.keys())}")
        raise OpenPLZPayloadError(endpoint, page, f"unexpected paged payload type: {type(payload).__name__}")

    def _validate_items(self, items: list[JsonValue], model: type[ModelT], *, endpoint: str, page: int) -> list[ModelT]:
        """Validate raw items against `model`, wrapping failures in `OpenPLZPayloadError`."""
        try:
            return [model.model_validate(item) for item in items]
        except ValidationError as exc:
            raise OpenPLZPayloadError(endpoint, page, str(exc)) from exc

    def _get_json(self, endpoint: str, params: _QueryParams | None = None) -> JsonValue:
        """Fetch one endpoint and parse its JSON body."""
        url = self._make_url(endpoint, params)
        body_text = self._fetch_text(url=url)
        parsed: JsonValue = json.loads(body_text)
        return parsed

    def _make_url(self, endpoint: str, params: _QueryParams | None) -> str:
        endpoint = endpoint.lstrip("/")
        path = f"/{self._language}/{endpoint}"
        url = f"{self._base_url}{path}"
        if params:
            # urlencode keeps page/pageSize param names as per OpenPLZ docs.
            url = f"{url}?{urllib.parse.urlencode(params)}"
        return url

    def _fetch_text(self, *, url: str) -> str:
        self._limiter.wait()
        req = urllib.request.Request(url, headers=self._headers)
        try:
            with urllib.request.urlopen(req, timeout=self._timeout_s) as resp:
                status: int = resp.status
                body_bytes: bytes = resp.read()
                body_text: str = body_bytes.decode("utf-8")
                if status < 200 or status >= 300:
                    raise OpenPLZHTTPError(status, body_text, url)
                return body_text
        except urllib.error.HTTPError as e:
            body_text = ""
            try:
                body_text = e.read().decode("utf-8")
            except Exception:
                body_text = str(e)
            raise OpenPLZHTTPError(e.code or 0, body_text, url) from e
