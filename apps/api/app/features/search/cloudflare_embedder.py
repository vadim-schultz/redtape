"""The Workers AI query embedder: one synchronous call with a timeout, secrets scrubbed from every message."""

from __future__ import annotations

import logging

import httpx
from pydantic import BaseModel, ValidationError

from app.features.search.query import NormalisedQuery
from app.features.search.query_embedder import QueryVector, instructed

logger = logging.getLogger(__name__)

API_ROOT = "https://api.cloudflare.com/client/v4/accounts"


class _Result(BaseModel):
    data: list[list[float]]


class _Answer(BaseModel):
    success: bool
    result: _Result


class CloudflareQueryEmbedder:
    """Embed a query with one Workers AI model; any failure is logged without secrets and answered with ``None``."""

    def __init__(
        self, account_id: str, token: str, model: str, *, dim: int, timeout_s: float, http: httpx.Client | None = None
    ) -> None:
        """Keep the credentials, the ``model``, the expected vector width ``dim`` and the request timeout."""
        self._account_id = account_id
        self._token = token
        self._model = model
        self._dim = dim
        self._timeout = timeout_s
        self._http = http or httpx.Client(trust_env=True)

    def embed(self, query: NormalisedQuery) -> QueryVector | None:
        """Return the vector of ``query``, or ``None`` on a timeout, an error status or an unusable answer."""
        try:
            response = self._post(instructed(query))
            return self._vector(response)
        except (httpx.HTTPError, ValueError) as error:
            logger.warning("query embedding failed: %s", self._scrub(f"{type(error).__name__}: {error}"))
            return None

    def _post(self, text: str) -> httpx.Response:
        response = self._http.post(
            f"{API_ROOT}/{self._account_id}/ai/run/{self._model}",
            json={"text": [text]},
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=self._timeout,
        )
        response.raise_for_status()
        return response

    def _vector(self, response: httpx.Response) -> QueryVector:
        """Return the one vector of a 2xx ``response``; raise :class:`ValueError` when it is not usable."""
        try:
            answer = _Answer.model_validate_json(response.content)
        except ValidationError as error:
            raise ValueError("the answer holds no embedding") from error
        vectors = answer.result.data
        if not answer.success or len(vectors) != 1 or len(vectors[0]) != self._dim:
            raise ValueError(f"expected one vector of {self._dim} numbers")
        return tuple(vectors[0])

    def _scrub(self, text: str) -> str:
        return text.replace(self._token, "<redacted>").replace(self._account_id, "<redacted>")
