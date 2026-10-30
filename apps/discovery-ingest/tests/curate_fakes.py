"""A recording stand-in for the machine API as ``candidates page`` and ``candidates curate`` use it."""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

API_BASE = "https://redtape.test"
API_KEY = "test-machine-key"
_REAL_HTTPX_CLIENT = httpx.Client
JURISDICTION = uuid.UUID(int=900)
SERVICE = uuid.UUID(int=100)
ARTIFACT = uuid.UUID(int=500)
HOST = "portal.example"
PAGE_URL = f"https://{HOST}/meldung"
MELDE, AUSWEIS, ANMELDUNG = (uuid.UUID(int=n) for n in (1, 2, 3))
EXCERPT_REQUIRES = "Bringen Sie Ihren Personalausweis mit."
EXCERPT_REQUIRED_BY = "Die Meldebescheinigung wird für die Anmeldung einer Wohnung benötigt."
HTML = (
    '<html lang="de"><head><title>Meldebescheinigung</title></head><body><nav>Menu</nav><main>'
    f"<h1>Meldebescheinigung</h1><p>Bringen Sie Ihren <b>Personalausweis</b> mit.</p><ul><li>{EXCERPT_REQUIRED_BY}</li>"
    "</ul></main><footer>Impressum</footer></body></html>"
)
STAGED = {
    MELDE: ("Meldebescheinigung", ["issued"]),
    AUSWEIS: ("Personalausweis", ["required"]),
    ANMELDUNG: ("Anmeldung einer Wohnung", ["form", "required"]),
}
TAXONOMY = {
    "domains": [{"code": "identity-civil-status", "name_i18n": {"de": "Identität"}, "description_i18n": {}}],
    "situations": [{"code": "moving-house", "name_i18n": {"de": "Umzug"}, "description_i18n": {}}],
}


def _slug(title: str) -> str:
    folded = title.lower().replace("ä", "a").replace("ö", "o").replace("ü", "u")
    return re.sub(r"[^a-z0-9]+", "-", folded).strip("-")


class Api:
    """Serves the reads curation needs and records every request; mentions and edges are remembered to answer replays."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.sources = {MELDE: [SERVICE]}
        self.seen_mentions: set[tuple[str, str, str, str]] = set()
        self.seen_edges: set[tuple[str, str, str]] = set()
        self.skip_required: set[str] = set()
        self.unknown_codes = 0

    def handler(self, request: httpx.Request) -> httpx.Response:
        """Answer one request; unknown routes are a 500 so a stray call fails loudly."""
        self.requests.append(request)
        path = request.url.path.removeprefix("/api/v1/discovery/machine")
        routes = {
            ("GET", "/taxonomy"): lambda: httpx.Response(200, json=TAXONOMY),
            ("GET", "/candidates/"): lambda: self._staged(),
            ("GET", "/candidates/sources"): lambda: self._sources(request),
            ("GET", "/artifacts"): lambda: self._artifacts(),
            ("GET", f"/artifacts/{ARTIFACT}/content"): lambda: httpx.Response(
                200, content=HTML.encode(), headers={"content-type": "text/html; charset=utf-8"}
            ),
            ("POST", "/candidates/mentions"): lambda: self._mentions(request),
            ("POST", "/candidates/edges"): lambda: self._edges(request),
        }
        return routes.get((request.method, path), lambda: httpx.Response(500, text=f"no stub {path}"))()

    def _staged(self) -> httpx.Response:
        items = [
            {
                "id": str(cid),
                "jurisdiction_id": str(JURISDICTION),
                "key": _slug(title),
                "title_i18n": {"de": title},
                "mention_count": 3,
                "roles": roles,
            }
            for cid, (title, roles) in STAGED.items()
        ]
        return httpx.Response(200, json={"items": items, "total": len(items), "offset": 0, "limit": 100})

    def _sources(self, request: httpx.Request) -> httpx.Response:
        wanted = uuid.UUID(request.url.params["candidate_id"])
        row = {"source_url": PAGE_URL, "host": HOST, "has_screenshot": False, "mention_count": 3}
        items = [{"catalogue_service_id": str(s), **row} for s in self.sources.get(wanted, [])]
        return httpx.Response(200, json={"items": items, "total": len(items), "offset": 0, "limit": 100})

    def _artifacts(self) -> httpx.Response:
        now = datetime.now(UTC).isoformat()
        item = {
            "id": str(ARTIFACT), "catalogue_service_id": str(SERVICE), "discovery_task_id": None, "kind": "html_snapshot",
            "sha256": "abc", "content_type": "text/html", "byte_size": len(HTML), "source_url": PAGE_URL,
            "final_url": None, "fetched_at": now,
        }  # fmt: skip
        return httpx.Response(200, json={"items": [item], "total": 1, "offset": 0, "limit": 100})

    def _mentions(self, request: httpx.Request) -> httpx.Response:
        items = json.loads(request.content)["items"]
        keys = [(i["catalogue_service_id"], _slug(i["title_i18n"]["de"]), i["role"], i["source_field"]) for i in items]
        replayed = sum(key in self.seen_mentions for key in keys)
        self.seen_mentions.update(keys)
        body = {"candidates_created": 0, "mentions_created": len(keys) - replayed, "mentions_updated": replayed}
        return httpx.Response(200, json={**body, "unknown_codes": self.unknown_codes})

    def _edges(self, request: httpx.Request) -> httpx.Response:
        items = json.loads(request.content)["items"]
        skipped = [
            {"index": n, "reason": "unknown_parent"}
            for n, item in enumerate(items)
            if item["required_title_i18n"]["de"] in self.skip_required
        ]
        keys = [self._edge_key(item) for n, item in enumerate(items) if n not in {s["index"] for s in skipped}]
        replayed = sum(key in self.seen_edges for key in keys)
        self.seen_edges.update(keys)
        body = {"edges_created": len(keys) - replayed, "edges_updated": replayed}
        return httpx.Response(200, json={**body, "edges_skipped": len(skipped), "skipped": skipped})

    @staticmethod
    def _edge_key(item: dict[str, Any]) -> tuple[str, str, str]:
        return (
            item["catalogue_service_id"],
            _slug(item["parent_title_i18n"]["de"]),
            _slug(item["required_title_i18n"]["de"]),
        )

    @property
    def posts(self) -> list[httpx.Request]:
        """The write requests, in order."""
        return [r for r in self.requests if r.method == "POST"]

    def bodies(self, suffix: str) -> list[dict[str, Any]]:
        """The JSON bodies posted to the route ending in ``suffix``, in order."""
        return [json.loads(r.content) for r in self.posts if r.url.path.endswith(suffix)]


def install(monkeypatch: pytest.MonkeyPatch) -> Api:
    """Point the client at a fresh :class:`Api` and set the two settings the commands read."""
    monkeypatch.setenv("DISCOVERY_API_URL", API_BASE)
    monkeypatch.setenv("DISCOVERY_API_KEY", API_KEY)
    fake = Api()

    def factory(**kwargs: Any) -> httpx.Client:
        kwargs["transport"] = httpx.MockTransport(fake.handler)
        return _REAL_HTTPX_CLIENT(**kwargs)

    monkeypatch.setattr("discovery_ingest.api_client.httpx.Client", factory)
    return fake


def edge(title: str, excerpt: str, **extra: object) -> dict[str, object]:
    """Return one curation edge entry."""
    return {"title_de": title, "excerpt": excerpt, "condition": None, "is_optional": False, **extra}


def entry(**changes: object) -> dict[str, object]:
    """Return a valid curation candidate for Meldebescheinigung; ``changes`` override its fields."""
    base: dict[str, object] = {
        "candidate_id": str(MELDE),
        "catalogue_service_id": str(SERVICE),
        "title_de": "Meldebescheinigung",
        "domain_codes": ["identity-civil-status"],
        "situation_codes": ["moving-house"],
        "tag_note": "issued when moving",
        "requires": [edge("Personalausweis", EXCERPT_REQUIRES)],
        "required_by": [edge("Anmeldung einer Wohnung", EXCERPT_REQUIRED_BY)],
    }
    return {**base, **changes}


def write_file(directory: Path, *candidates: dict[str, object], **top: object) -> Path:
    """Write a curation file holding ``candidates`` under ``directory`` and return its path."""
    path = directory / "curation.json"
    body = {"version": 1, "curator": "test 2026-10-30", "candidates": list(candidates), **top}
    path.write_text(json.dumps(body), encoding="utf-8")
    return path
