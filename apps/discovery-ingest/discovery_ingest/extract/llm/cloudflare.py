"""The Workers AI adapter: the only module that knows the bearer token, the endpoint paths and the envelope."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx

from discovery_ingest.browser.throttle import Throttle
from discovery_ingest.extract.llm.classify import error_for
from discovery_ingest.extract.llm.client import LlmResult
from discovery_ingest.extract.llm.endpoints import endpoint_url
from discovery_ingest.extract.llm.envelope import read_result
from discovery_ingest.extract.llm.errors import LlmRequestError
from discovery_ingest.extract.llm.payloads import run_body
from discovery_ingest.extract.llm.schema_prep import prepare_schema
from discovery_ingest.llm_settings import LlmSettings

DEFAULT_MIN_INTERVAL_SECONDS = 1.0


class CloudflareAiClient:
    """Call one Workers AI model in JSON mode, one throttled request at a time."""

    def __init__(
        self,
        settings: LlmSettings,
        *,
        model: str | None = None,
        http: httpx.Client | None = None,
        throttle: Throttle | None = None,
    ) -> None:
        """Wire the credentials and the model (missing ones raise :class:`ValueError`), the throttle and HTTP."""
        self._account_id, self._token = settings.ai_credentials()
        chosen = model or settings.llm_model
        if not chosen:
            raise ValueError("no model: pass one or set LLM_MODEL")
        self._model = chosen
        self._timeout = settings.llm_request_timeout_seconds
        self._http = http or httpx.Client(trust_env=True)
        self._throttle = throttle or Throttle(DEFAULT_MIN_INTERVAL_SECONDS)

    def extract(self, messages: Sequence[dict[str, str]], json_schema: dict[str, Any], *, max_tokens: int) -> LlmResult:
        """Return the model's JSON answer and usage, or raise the :class:`LlmError` the response stands for."""
        body = run_body(messages, prepare_schema(json_schema), max_tokens)
        response = self._post(body)
        if response.status_code >= 400:
            raise error_for(response, self._scrub)
        return read_result(response, self._model)

    def _post(self, body: dict[str, Any]) -> httpx.Response:
        with self._throttle:
            try:
                return self._http.post(
                    endpoint_url(self._account_id, "run", self._model),
                    json=body,
                    headers={"Authorization": f"Bearer {self._token}"},
                    timeout=self._timeout,
                )
            except httpx.HTTPError as err:
                raise LlmRequestError(self._scrub(f"{type(err).__name__}: {err}"), retryable=True) from err

    def _scrub(self, text: str) -> str:
        return text.replace(self._token, "<redacted>").replace(self._account_id, "<redacted>")
