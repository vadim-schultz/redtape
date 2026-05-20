from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable
from typing import Any, Callable, Protocol, TypeVar

TParsed = TypeVar("TParsed")


class OpenPLZHTTPError(RuntimeError):
    def __init__(self, status: int, body: str, url: str) -> None:
        super().__init__(f"OpenPLZ request failed: status={status} url={url} body={body[:500]}")
        self.status = status
        self.body = body
        self.url = url


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
    """
    Minimal OpenPLZ client for import jobs.

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
        self._base_url = base_url.rstrip("/")
        self._language = language.strip("/")
        self._timeout_s = timeout_s
        self._headers = {
            "Accept": "application/json",
            "User-Agent": user_agent,
        }
        self._limiter = _RateLimiter(rate_limit_rps)

    def _make_url(self, endpoint: str, params: dict[str, Any] | None) -> str:
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
                status = resp.status
                body_bytes = resp.read()
                body_text = body_bytes.decode("utf-8")
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

    def _parse_json(self, body_text: str) -> Any:
        return json.loads(body_text)

    def get_json(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        url = self._make_url(endpoint, params)
        body_text = self._fetch_text(url=url)
        return self._parse_json(body_text)

    def _select_paged_payload_handler(
        self, payload: Any
    ) -> Callable[[Any], list[Any]]:
        """
        Small adapter/factory: choose the appropriate extraction handler
        based on the payload runtime shape.
        """
        if isinstance(payload, list):
            return self._handle_paged_list_payload
        if isinstance(payload, dict):
            return self._handle_paged_dict_payload
        return self._handle_paged_unknown_payload

    def _handle_paged_list_payload(self, payload: list[Any]) -> list[Any]:
        return payload or []

    def _handle_paged_dict_payload(self, payload: dict[str, Any]) -> list[Any]:
        # Common shapes:
        # - {"items": [...]} (common)
        # - {"data": [...]} (fallback)
        items = payload.get("items")
        if isinstance(items, list):
            return items

        data = payload.get("data")
        if isinstance(data, list):
            return data

        raise RuntimeError(f"Unexpected paged payload shape: keys={list(payload.keys())}")

    def _handle_paged_unknown_payload(self, payload: Any) -> list[Any]:
        raise RuntimeError(f"Unexpected paged payload type: {type(payload)}")

    def _extract_paged_items(self, payload: Any) -> list[Any]:
        """Extract the list of items from an OpenPLZ paged response payload."""
        handler = self._select_paged_payload_handler(payload)
        return handler(payload)

    def iter_paged(
        self,
        *,
        endpoint: str,
        params: dict[str, Any] | None = None,
        page_size: int = 50,
        max_pages: int | None = 10_000,
        item_parser: Callable[[Any], TParsed] | None = None,
    ) -> Iterable[TParsed]:
        """
        Iterate over OpenPLZ endpoints that support paging.

        Paging query params are `page` and `pageSize` (per OpenPLZ docs).
        """

        page = 1
        while True:
            effective_params: dict[str, Any] = dict(params or {})
            effective_params["page"] = page
            effective_params["pageSize"] = page_size
            payload = self.get_json(endpoint, effective_params)
            items = self._extract_paged_items(payload)
            if not items:
                return

            for item in items:
                if item_parser is None:
                    yield item
                else:
                    yield item_parser(item)

            page += 1
            if max_pages is not None and page > max_pages:
                return

