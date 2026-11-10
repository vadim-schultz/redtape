"""The Workers AI embedding adapter: one throttled ``/ai/run`` call per batch of texts."""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass

import httpx

from discovery_ingest.browser.throttle import Throttle
from discovery_ingest.extract.embedding.response import Vector, read_embeddings
from discovery_ingest.extract.llm.classify import error_for
from discovery_ingest.extract.llm.endpoints import endpoint_url
from discovery_ingest.extract.llm.errors import LlmRequestError
from discovery_ingest.extract.llm.payloads import Body
from discovery_ingest.llm_settings import LlmSettings

DEFAULT_MIN_INTERVAL_SECONDS = 0.2


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    """One vector per input text in input order, their dimension, and the usage the provider reported (else ``None``)."""

    vectors: tuple[Vector, ...]
    dimension: int
    model: str
    input_tokens: int | None
    neurons: float | None
    latency_ms: int


def embed_body(texts: Sequence[str], dimensions: int | None) -> Body:
    """Return the ``/ai/run`` body: the ``text`` batch and, when reduced, the Matryoshka ``dimensions``."""
    body: Body = {"text": list(texts)}
    if dimensions is not None:
        body["dimensions"] = dimensions
    return body


class CloudflareEmbeddingClient:
    """Embed batches of texts with one Workers AI model, one throttled request at a time."""

    def __init__(
        self,
        settings: LlmSettings,
        *,
        model: str | None = None,
        http: httpx.Client | None = None,
        throttle: Throttle | None = None,
    ) -> None:
        """Wire the credentials (missing ones raise :class:`ValueError`), the model, the throttle and HTTP."""
        self._account_id, self._token = settings.ai_credentials()
        self._model = model or settings.embedding_model
        self._timeout = settings.llm_request_timeout_seconds
        self._http = http or httpx.Client(trust_env=True)
        self._throttle = throttle or Throttle(DEFAULT_MIN_INTERVAL_SECONDS)

    def embed(self, texts: Sequence[str], *, dimensions: int | None = None) -> EmbeddingResult:
        """Return the vectors of ``texts`` (reduced to ``dimensions`` when given), or raise the error the response is."""
        if not texts:
            raise ValueError("no texts to embed")
        response, latency_ms = self._timed_answer(embed_body(texts, dimensions))
        parsed = read_embeddings(response, len(texts))
        return EmbeddingResult(
            parsed.vectors, parsed.dimension, self._model, parsed.input_tokens, parsed.neurons, latency_ms
        )

    def _timed_answer(self, body: Body) -> tuple[httpx.Response, int]:
        """Return the 2xx response and its wall time in milliseconds, or raise the typed error of a failed one."""
        started = time.monotonic()
        response = self._post(body)
        latency_ms = round((time.monotonic() - started) * 1000)
        if response.status_code >= 400:
            raise error_for(response, self._scrub)
        return response, latency_ms

    def _post(self, body: Body) -> httpx.Response:
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
