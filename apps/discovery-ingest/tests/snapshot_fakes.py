"""Fakes for the snapshot drain tests: the snapshot routes and the artifact content route behind one mock transport, a
scripted Azure engine, and procedure-page HTML.

The budget routes are served by the shared :class:`FakeLedger`, so the real guard, meter and character ledger run.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import httpx
import pytest
from discovery_ingest.client import DiscoveryIngestClient
from discovery_ingest.translation.errors import TranslationEngineError
from discovery_ingest.translation.units import (
    CallLimits,
    TranslationBatch,
    TranslationOutcome,
    TranslationUnit,
    Usage,
    UsageUnit,
)
from pydantic import SecretStr

from ledger_fakes import FakeLedger
from run_stub import run_response
from translate_fakes import API_BASE, API_KEY, AZURE_HOST

ENGINE = "azure-translator"
PAGE_ENGINE_UNIT: UsageUnit = "characters"
VANISH = "VANISH"
"""A source text containing this word comes back empty from :class:`ScriptedAzure`, so its block fails validation."""
_REAL_HTTPX_CLIENT = httpx.Client
Handler = Callable[[httpx.Request], httpx.Response]
EXPECTED_KINDS = ["h1", "p", "p", "p", "h2", "li", "li", "row", "row", "p"]
"""The block kinds of :func:`page_html`, in document order."""


def task_id(number: int) -> str:
    """The id of the snapshot task ``snapshot_task(number)``."""
    return str(uuid.UUID(int=7000 + number))


def artifact_id(number: int) -> str:
    """The id of the stored snapshot the task ``number`` names."""
    return str(uuid.UUID(int=8000 + number))


def page_url(number: int) -> str:
    """The address the page of task ``number`` was fetched from."""
    return f"https://www.example.de/seite-{number}"


def sha(number: int) -> str:
    """The raw artifact sha256 of task ``number``: 64 hex characters, as the API stores it."""
    return hashlib.sha256(f"raw-{number}".encode()).hexdigest()


def snapshot_task(number: int, locale: str = "en", *, stored: str | None = None) -> dict[str, Any]:
    """A claimed snapshot task as the claim route hands it out; ``stored`` is the cleaned-text hash already stored."""
    return {
        "task_id": task_id(number),
        "catalogue_service_id": str(uuid.UUID(int=6000 + number)),
        "locale": locale,
        "source_locale": "de",
        "artifact_id": artifact_id(number),
        "artifact_sha256": sha(number),
        "source_url": page_url(number),
        "stored_source_hash": stored,
        "lease_expires_at": "2026-11-10T12:00:00Z",
    }


def page_html(*, lang: str = "de", extra: str = "") -> str:
    """A German procedure page with a heading, paragraphs, a list, a table row pair and a link; ``extra`` is appended."""
    return f"""<!doctype html><html lang="{lang}"><head><title>Reisepass</title></head><body>
<nav>Menü Start</nav>
<h1>Reisepass beantragen</h1>
<p>Der Antrag auf einen Reisepass wird im Bürgeramt gestellt, Schritt 1. Bitte bringen Sie alle Unterlagen mit.</p>
<p>Der Antrag auf einen Reisepass wird im Bürgeramt gestellt, Schritt 2. Bitte bringen Sie alle Unterlagen mit.</p>
<p>Der Antrag auf einen Reisepass wird im Bürgeramt gestellt, Schritt 3. Bitte bringen Sie alle Unterlagen mit.</p>
<h2>Gebühren</h2>
<ul><li>Erwachsene: 60 Euro</li><li>Kinder: 37,50 Euro</li></ul>
<table><tr><th>Art</th><th>Preis</th></tr><tr><td>Express</td><td>32 Euro</td></tr></table>
<p>Mehr unter <a href="https://www.example.de/info">Infos</a>.</p>
{extra}
<footer>Impressum</footer>
</body></html>"""


def short_page() -> str:
    """A German page whose cleaned text is far under the 200 characters the pipeline needs."""
    return '<html lang="de"><body><h1>Wartung</h1><p>Kurz.</p></body></html>'


class SnapshotApi:
    """The snapshot routes, the artifact content route and the budget ledger behind one mock transport.

    ``pages`` maps a task number to the stored HTML its artifact holds; a task whose page is absent gets a 404 (pruned).
    ``outcomes`` replaces the answer of a task's item in ``complete``; by default each item answers its own outcome.
    """

    def __init__(
        self,
        tasks: Sequence[dict[str, Any]],
        pages: Mapping[int, str],
        *,
        ledger: FakeLedger | None = None,
    ) -> None:
        self.queue = list(tasks)
        self.pages = {artifact_id(number): html for number, html in pages.items()}
        self.ledger = ledger or FakeLedger(9000.0, characters=1_900_000.0)
        self.outcomes: dict[str, tuple[str, str | None]] = {}
        self.fetched: list[str] = []
        self.paths: list[str] = []
        self.bodies: dict[str, list[dict[str, Any]]] = defaultdict(list)

    def handler(self, request: httpx.Request) -> httpx.Response:
        """Serve the budget routes, the content route and the snapshot routes; anything else is a 404."""
        path = request.url.path
        self.paths.append(path)
        if "/budgets" in path:
            return self.ledger(request)
        if (run := run_response(request)) is not None:
            return run
        if path.endswith("/content"):
            return self._content(path.rsplit("/", 2)[-2])
        if "/snapshots/" not in path:
            return httpx.Response(404, json={"detail": "not a snapshot route"})
        route = path.rsplit("/", 1)[-1]
        body = json.loads(request.content) if request.content else {}
        self.bodies[route].append(body)
        return getattr(self, f"_{route}")(body)

    def client(self) -> DiscoveryIngestClient:
        """A machine client whose transport is this API."""
        return DiscoveryIngestClient(API_BASE, SecretStr(API_KEY), transport=httpx.MockTransport(self.handler))

    def install(self, monkeypatch: pytest.MonkeyPatch, azure: Handler | None = None) -> None:
        """Route every ``httpx.Client`` the code under test builds: Azure calls to ``azure``, the rest to this API."""

        def route(request: httpx.Request) -> httpx.Response:
            if azure is not None and request.url.host == AZURE_HOST:
                return azure(request)
            return self.handler(request)

        def factory(**kwargs: Any) -> httpx.Client:
            kwargs["transport"] = httpx.MockTransport(route)
            return _REAL_HTTPX_CLIENT(**kwargs)

        monkeypatch.setattr("discovery_ingest.client.http_client.httpx.Client", factory)

    def posted(self) -> list[dict[str, Any]]:
        """Every item posted to ``complete``, in order."""
        return [item for body in self.bodies["complete"] for item in body["items"]]

    def _content(self, identifier: str) -> httpx.Response:
        self.fetched.append(identifier)
        html = self.pages.get(identifier)
        if html is None:
            return httpx.Response(404, json={"detail": "Unknown artifact"})
        return httpx.Response(200, content=html.encode(), headers={"content-type": "text/html; charset=utf-8"})

    def _claim(self, body: dict[str, Any]) -> httpx.Response:
        taken, self.queue = self.queue[: body["limit"]], self.queue[body["limit"] :]
        return httpx.Response(200, json={"items": taken})

    def _complete(self, body: dict[str, Any]) -> httpx.Response:
        return httpx.Response(200, json={"items": [self._result(item) for item in body["items"]]})

    def _result(self, item: dict[str, Any]) -> dict[str, Any]:
        identifier = item["task_id"]
        outcome, reason = self.outcomes.get(identifier, (_ANSWER[item["outcome"]], None))
        return {"task_id": identifier, "outcome": outcome, "reason": reason}

    def _fail(self, body: dict[str, Any]) -> httpx.Response:
        status = "pending" if body["retryable"] else "failed"
        return httpx.Response(200, json={"task_id": body["task_id"], "status": status, "last_error": body["error"]})

    def _release(self, body: dict[str, Any]) -> httpx.Response:
        return httpx.Response(200, json={"released": body["task_ids"], "skipped": []})

    def _summary(self, _body: dict[str, Any]) -> httpx.Response:
        row = {"pending_ready": len(self.queue), "claimed": 0, "failed": 0, "translated": 0, "stale": 0, "skipped": 0}
        return httpx.Response(200, json={"locales": [{"locale": "en", **row}]})


_ANSWER = {"translated": "stored", "unchanged": "unchanged", "skipped": "skipped"}
"""The answer a complete item gets when the test does not script one: each outcome answers as itself."""


def _chars(batch: TranslationBatch) -> int:
    return sum(len(unit.title) for unit in batch.units)


def _render(locale: str, text: str) -> str:
    return "" if VANISH in text else f"[{locale}] {text}"


class ScriptedAzure:
    """An Azure engine for tests: it renders each text behind its locale and bills ``billed`` times the characters sent.

    ``outcomes`` are raised or served per call (``None`` is a normal answer; the last one repeats). ``short`` drops the
    last unit of each call, so the answer is one result short. Texts containing :data:`VANISH` come back empty.
    """

    name = ENGINE
    usage_unit: UsageUnit = PAGE_ENGINE_UNIT
    repairs = False

    def __init__(self, *outcomes: TranslationEngineError | None, billed: float = 1.0, short: bool = False) -> None:
        self.outcomes = list(outcomes) or [None]
        self.billed = billed
        self.short = short
        self.batches: list[TranslationBatch] = []
        self.billed_total = 0.0
        self.estimated_total = 0.0

    @property
    def limits(self) -> CallLimits:
        """One call at a time, of up to 50 units, as the Azure adapter has it."""
        return CallLimits(units_per_call=50, concurrency=1)

    def estimate(self, batch: TranslationBatch) -> Usage:
        """Reserve the source characters of the batch, as plain text is billed."""
        return Usage(self.usage_unit, float(_chars(batch)))

    def translate(self, batch: TranslationBatch) -> TranslationOutcome:
        """Record the batch, raise the scripted error, or return one result per unit (one fewer when short)."""
        self.batches.append(batch)
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if outcome is not None:
            raise outcome
        units = batch.units[:-1] if self.short else batch.units
        results = tuple(TranslationUnit(unit.key, _render(batch.target_locale, unit.title), "") for unit in units)
        billed = _chars(batch) * self.billed
        self.billed_total += billed
        self.estimated_total += _chars(batch)
        return TranslationOutcome(results, Usage(self.usage_unit, billed), None)
