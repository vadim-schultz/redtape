"""One fake transport per registered adapter: what the conformance suite needs to drive a real adapter without a network.

To add an adapter, add its harness to :data:`HARNESSES` under its registry name.
"""

from __future__ import annotations

import json
from enum import StrEnum
from typing import Protocol

import httpx
from discovery_ingest.translation.adapters.cloudflare_llm import LlmTranslator
from discovery_ingest.translation.engine import TranslationEngine

from llm_transport import MODEL, TOKEN, client, failure, success


class Behaviour(StrEnum):
    """How the fake provider answers the next batch."""

    FAITHFUL = "faithful"
    SHORT = "short"
    QUOTA = "quota"
    TRANSIENT = "transient"
    UNAUTHORISED = "unauthorised"
    PERMANENT = "permanent"


FAILURES = (Behaviour.QUOTA, Behaviour.TRANSIENT, Behaviour.UNAUTHORISED, Behaviour.PERMANENT)


class AdapterHarness(Protocol):
    """What the conformance suite needs: the registry name, the secret to look for, and an engine over a fake transport."""

    name: str
    secret: str

    def build(self, behaviour: Behaviour) -> TranslationEngine:
        """Return the adapter wired to a fake transport that answers with ``behaviour``."""
        ...


def _units_in(request: httpx.Request) -> list[dict[str, str]]:
    """Return the units the adapter put into its user message."""
    messages = json.loads(request.content)["messages"]
    return json.loads(messages[-1]["content"])["units"]


def _tag(text: str) -> str:
    return f"[en] {text}" if text else ""


def _faithful(units: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    """Translate by prefixing: every character of the source, including numbers and citations, survives."""
    return {
        "units": [
            {"key": u["key"], "title": f"[en] {u['title']}", "description": _tag(u["description"])} for u in units
        ]
    }


_ERRORS: dict[Behaviour, tuple[int, int, str]] = {
    Behaviour.QUOTA: (429, 4006, "you have used up your daily free allocation"),
    Behaviour.TRANSIENT: (503, 1000, "service unavailable"),
    Behaviour.UNAUTHORISED: (401, 10000, "authentication error"),
    Behaviour.PERMANENT: (400, 5006, "bad request"),
}


class CloudflareLlmHarness:
    """The Cloudflare LLM adapter over an ``httpx`` mock transport; every error body echoes the token."""

    name = "llm"
    secret = TOKEN

    def build(self, behaviour: Behaviour) -> TranslationEngine:
        """Return an :class:`LlmTranslator` whose HTTP is the mock transport for ``behaviour``."""

        def handler(request: httpx.Request) -> httpx.Response:
            if behaviour in _ERRORS:
                status, code, message = _ERRORS[behaviour]
                return failure(status, code, f"{message} (token {TOKEN})")
            units = _units_in(request)
            answered = units[:-1] if behaviour is Behaviour.SHORT else units
            usage = {
                "prompt_tokens": 100 * len(units),
                "completion_tokens": 80 * len(units),
                "neurons": 1.5 * len(units),
            }
            return success(_faithful(answered), usage)

        return LlmTranslator(client(handler), model=MODEL, max_tokens=2000)


HARNESSES: dict[str, AdapterHarness] = {"llm": CloudflareLlmHarness()}
