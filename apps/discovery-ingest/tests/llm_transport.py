"""A Workers AI client wired to a mock transport, shared by the client, meter and probe tests."""

from __future__ import annotations

from collections.abc import Callable

import httpx
from discovery_ingest.browser.throttle import Throttle
from discovery_ingest.extract.llm.cloudflare import CloudflareAiClient
from discovery_ingest.llm_settings import LlmSettings

ACCOUNT_ID = "acc0123456789abcdef0123456789abc"
TOKEN = "ai-tok-SECRET-0123456789"
MODEL = "@cf/meta/llama-3.1-8b-instruct"
Handler = Callable[[httpx.Request], httpx.Response]
MESSAGES = [{"role": "system", "content": "extract"}, {"role": "user", "content": "page"}]
SCHEMA = {"type": "object", "properties": {"page_kind": {"type": "string"}}, "required": ["page_kind"]}


def settings(**overrides: object) -> LlmSettings:
    """Settings with both credentials set (the values are what the redaction tests look for)."""
    fields: dict[str, object] = {"CLOUDFLARE_ACCOUNT_ID": ACCOUNT_ID, "CLOUDFLARE_AI_API_TOKEN": TOKEN, **overrides}
    return LlmSettings.model_validate(fields)


def success(response: object, usage: dict[str, int] | None = None) -> httpx.Response:
    """A native ``/ai/run`` answer: ``result.response`` and, when given, ``result.usage``."""
    result: dict[str, object] = {"response": response}
    if usage is not None:
        result["usage"] = usage
    return httpx.Response(200, json={"result": result, "success": True, "errors": [], "messages": []})


def failure(status: int, code: int, message: str, headers: dict[str, str] | None = None) -> httpx.Response:
    """A Cloudflare error envelope with one error."""
    body = {"result": None, "success": False, "errors": [{"code": code, "message": message}], "messages": []}
    return httpx.Response(status, json=body, headers=headers)


def client(handler: Handler, *, model: str | None = MODEL, sleeps: list[float] | None = None) -> CloudflareAiClient:
    """A client whose HTTP is ``handler`` and whose throttle never really sleeps."""
    sleeps = sleeps if sleeps is not None else []
    throttle = Throttle(1.0, clock=lambda: 0.0, sleep=sleeps.append)
    return CloudflareAiClient(
        settings(), model=model, http=httpx.Client(transport=httpx.MockTransport(handler)), throttle=throttle
    )
