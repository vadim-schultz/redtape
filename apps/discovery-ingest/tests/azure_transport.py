"""An Azure Translator engine wired to a mock transport, shared by the adapter's tests: it answers like API 2026-06-06."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping

import httpx
from discovery_ingest.browser.throttle import Throttle
from discovery_ingest.translation.adapters.azure_translator import AzureTranslator
from discovery_ingest.translation.adapters.azure_translator_http import AzureConnection, AzureTransport

KEY = "azure-key-SECRET-0123456789"
REGION = "westeurope"
ENDPOINT = "https://api.cognitive.microsofttranslator.com"
API_VERSION = "2026-06-06"
Handler = Callable[[httpx.Request], httpx.Response]


def connection(key: str = KEY) -> AzureConnection:
    """The connection the tests use: the global host, the pinned API version and the test key and region."""
    return AzureConnection(endpoint=ENDPOINT, api_version=API_VERSION, key=key, region=REGION)


def engine(handler: Handler, *, sleeps: list[float] | None = None, key: str = KEY) -> AzureTranslator:
    """An engine whose HTTP is ``handler``; its throttle never really sleeps and records the waits in ``sleeps``."""
    waits = sleeps if sleeps is not None else []
    throttle = Throttle(1.0, clock=lambda: 0.0, sleep=waits.append)
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return AzureTranslator(AzureTransport(connection(key), throttle, http))


def inputs_in(request: httpx.Request) -> list[dict[str, object]]:
    """The inputs of one translate request, as the adapter sent them."""
    body: Mapping[str, list[dict[str, object]]] = json.loads(request.content)
    return body["inputs"]


def faithful_answer(request: httpx.Request, *, drop: int = 0, metered: float | None = None) -> httpx.Response:
    """Answer every input with its text behind ``[en] ``, minus the last ``drop`` answers.

    The billed characters default to the characters of the inputs, which is what the service reports for plain text.
    """
    inputs = inputs_in(request)
    answers = [_answer_for(item) for item in inputs[: len(inputs) - drop]]
    billed = sum(len(str(item["text"])) for item in inputs) if metered is None else metered
    return httpx.Response(200, json=answers, headers={"X-metered-usage": str(billed)})


def _answer_for(item: dict[str, object]) -> dict[str, object]:
    targets = item["targets"]
    assert isinstance(targets, list)
    target = targets[0]
    assert isinstance(target, dict)
    return {"translations": [{"text": f"[en] {item['text']}", "to": target["language"]}]}


def failure(status: int, code: str, message: str) -> httpx.Response:
    """An Azure error envelope with one error, as the service returns it."""
    return httpx.Response(status, json={"error": {"code": code, "message": message}})
